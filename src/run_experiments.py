"""实验入口。阶段：opt(生成+优化) -> eval(评测所有配置) -> judge(专家评分代理) -> 汇总见 report.py。
用法: python src/run_experiments.py opt|eval|judge|all"""
import json, os, sys, time

sys.path.insert(0, os.path.dirname(__file__))
from llm import JUDGE_MODEL, call, pmap, stats
from optimizer import optimize
from pipeline import run_plain, run_spec
from prompts import MANUAL_A, direct_llm_prompt, generate_initial_spec, manual_a2_system, render_system
from retrieval import ExampleStore, Glossary, load_jsonl
from scoring import aggregate, format_ok, instance_scores, parse_lenient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
os.makedirs(os.path.join(RES, "outputs"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "prompts"), exist_ok=True)


def jl(name):
    return load_jsonl(os.path.join(ROOT, "data", name + ".jsonl"))


TRAIN, TEST, HARD = jl("train"), jl("test"), jl("hard")
GLOSS = Glossary()
STORE = ExampleStore(TRAIN)
TOPICS = [e["term"] for e in GLOSS.items]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def save(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


# ------------------------------------------------------------------ 生成 + 优化
def stage_opt():
    out = {}
    for track, wc in (("std", True), ("cold", False)):
        spec0 = generate_initial_spec(TOPICS, with_constraints=wc)
        save(os.path.join(ROOT, "prompts", f"{track}_initial_spec.json"), spec0)
        out[f"{track}_initial"] = spec0
        for kb in (True, False):
            name = f"{track}_{'kb' if kb else 'nokb'}"
            log(f"=== 优化闭环: {name} ===")
            spec, info = optimize(spec0, TRAIN, GLOSS if kb else None, STORE if kb else None, log=log)
            save(os.path.join(ROOT, "prompts", f"{name}_optimized_spec.json"), spec)
            save(os.path.join(RES, f"opt_trace_{name}.json"), info)
            log(f"{name}: final train {info['final_train']} | 优化阶段 tokens={info['opt_tokens']} calls={info['opt_calls']}")


# ------------------------------------------------------------------ 配置
def spec_of(name):
    return json.load(open(os.path.join(ROOT, "prompts", name + ".json"), encoding="utf-8"))


def configs():
    direct = direct_llm_prompt()
    open(os.path.join(ROOT, "prompts", "direct_llm.txt"), "w", encoding="utf-8").write(direct)
    open(os.path.join(ROOT, "prompts", "manual_A.txt"), "w", encoding="utf-8").write(MANUAL_A)
    open(os.path.join(ROOT, "prompts", "manual_A2.txt"), "w", encoding="utf-8").write(manual_a2_system())
    S = lambda n: spec_of(n)
    C = {
        "A_manual":        lambda i: run_plain(MANUAL_A, i),
        "B_direct_llm":    lambda i: run_plain(direct, i),
        "A2_manual_schema": lambda i: run_plain(manual_a2_system(), i),
        "OURS":            lambda i, s=S("std_kb_optimized_spec"): run_spec(s, i, GLOSS, STORE, repair=True),
        "OURS_noKB":       lambda i, s=S("std_nokb_optimized_spec"): run_spec(s, i, None, None, repair=True),
        "OURS_noLoop":     lambda i, s=S("std_initial_spec"): run_spec(s, i, GLOSS, STORE, repair=True),
        "OURS_noRepair":   lambda i, s=S("std_kb_optimized_spec"): run_spec(s, i, GLOSS, STORE, repair=False),
        "COLD_gen_only":   lambda i, s=S("cold_initial_spec"): run_spec(s, i, None, None, repair=False),
        "COLD_KB":         lambda i, s=S("cold_initial_spec"): run_spec(s, i, GLOSS, STORE, repair=False),
        "COLD_loop":       lambda i, s=S("cold_nokb_optimized_spec"): run_spec(s, i, None, None, repair=False),
        "COLD_full":       lambda i, s=S("cold_kb_optimized_spec"): run_spec(s, i, GLOSS, STORE, repair=True),
        "COLD_full_noRepair": lambda i, s=S("cold_kb_optimized_spec"): run_spec(s, i, GLOSS, STORE, repair=False),
    }
    return C


def stage_eval():
    data = TEST + HARD
    allres = {}
    for name, fn in configs().items():
        outs = pmap(fn, data, workers=8)
        rows = []
        with open(os.path.join(RES, "outputs", name + ".jsonl"), "w", encoding="utf-8") as f:
            for o, inst in zip(outs, data):
                sc = instance_scores(parse_lenient(o["text"]), inst["gold"])
                row = dict(id=inst["id"], split="test" if inst in TEST else "hard", tags=inst["tags"], fmt_ok=int(format_ok(o["text"])),
                           parsed=int(parse_lenient(o["text"]) is not None), in_tok=o["in_tok"], out_tok=o["out_tok"], calls=o["calls"],
                           repaired=int(o["repaired"]), **sc)
                rows.append(row)
                f.write(json.dumps(dict(row, output=o["text"], v_errors=o.get("v_errors"), v_warns=o.get("v_warns")), ensure_ascii=False) + "\n")
        allres[name] = rows
        a = aggregate(rows)
        log(f"{name:20s} acc={a['acc']:.3f} f1={a['f1']:.3f} fmt={sum(r['fmt_ok'] for r in rows) / len(rows):.3f} tok={sum(r['in_tok'] + r['out_tok'] for r in rows) / len(rows):.0f}")
    save(os.path.join(RES, "eval_rows.json"), allres)


# ------------------------------------------------------------------ 专家评分代理(LLM 评审，盲评)
JUDGE_SYSTEM = "You are a senior materials scientist grading an information-extraction result. Reply with a single JSON object only."
JUDGE_USER = """Paragraph:
{text}

Reference answer (curated by the task author):
{gold}

Candidate answer:
{pred}

Grade the candidate from 1 to 5 as an expert would:
5 = scientifically correct and complete: right materials, values, units/conversions, method and gap type, no spurious records;
4 = minor issue (one wrong label or formatting slip) that would not mislead;
3 = partly correct: some correct records but a missing or extra record, or several wrong labels;
2 = mostly wrong or misleading;
1 = unusable (unparseable, hallucinated, or entirely wrong).
Return {{"score": int, "reason": "<=25 words"}}."""


def stage_judge(names=("A_manual", "B_direct_llm", "A2_manual_schema", "OURS")):
    data = {i["id"]: i for i in TEST + HARD}
    out = {}
    for n in names:
        rows = [json.loads(l) for l in open(os.path.join(RES, "outputs", n + ".jsonl"), encoding="utf-8")]
        def one(r):
            g = [{k: x[k] for k in ("material", "band_gap_eV", "method", "gap_type")} for x in data[r["id"]]["gold"]]
            resp = call(JUDGE_MODEL, JUDGE_SYSTEM, JUDGE_USER.format(text=data[r["id"]]["text"], gold=json.dumps(g, ensure_ascii=False), pred=r["output"]), max_tokens=300)
            t = resp["text"]
            try:
                return int(json.loads(t[t.find("{"): t.rfind("}") + 1])["score"])
            except Exception:
                return None
        scores = pmap(one, rows, workers=8)
        out[n] = {r["id"]: s for r, s in zip(rows, scores)}
        v = [s for s in scores if s is not None]
        log(f"judge {n}: mean={sum(v) / len(v):.2f} (n={len(v)})")
    save(os.path.join(RES, "judge_scores.json"), out)


if __name__ == "__main__":
    st = sys.argv[1] if len(sys.argv) > 1 else "all"
    if st in ("opt", "all"): stage_opt()
    if st in ("eval", "all"): stage_eval()
    if st in ("judge", "all"): stage_judge()
    log("API 统计:", stats())
