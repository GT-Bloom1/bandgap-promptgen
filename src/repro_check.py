"""可复现性检验(验证机制的“可复现性”一项)：同一方案、温度 0，用不同 sample_id 重复运行 70 条测试实例，
比较与首次运行(results/outputs/OURS.jsonl)的输出一致率与准确率波动。sample_id 只用于绕开缓存，不改变请求内容。
用法: python src/repro_check.py [重复次数，默认2]"""
import json, os, sys

sys.path.insert(0, os.path.dirname(__file__))
import llm, pipeline
from llm import pmap
from retrieval import ExampleStore, Glossary, load_jsonl
from scoring import aggregate, format_ok, instance_scores, parse_lenient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
jl = lambda n: load_jsonl(os.path.join(ROOT, "data", n + ".jsonl"))
DATA = jl("test") + jl("hard")
GLOSS, STORE = Glossary(), ExampleStore(jl("train"))
SPEC = json.load(open(os.path.join(ROOT, "prompts", "std_kb_optimized_spec.json"), encoding="utf-8"))


def canon(text):
    """规范化后的记录集合(材料名无关)，用于判断两次输出在科学内容上是否一致。"""
    recs = parse_lenient(text) or []
    return sorted((round(float(r.get("band_gap_eV", -1)), 2), r.get("method"), r.get("gap_type")) for r in recs if isinstance(r, dict) and isinstance(r.get("band_gap_eV"), (int, float)))


def run(sid):
    orig = llm.call
    pipeline.call = lambda *a, **k: orig(*a, sample_id=sid, **k)
    try:
        return pmap(lambda i: pipeline.run_spec(SPEC, i, GLOSS, STORE, repair=True), DATA, workers=8)
    finally:
        pipeline.call = orig


def main():
    n_rep = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    base = {}
    for l in open(os.path.join(RES, "outputs", "OURS.jsonl"), encoding="utf-8"):
        r = json.loads(l); base[r["id"]] = r["output"]
    runs = {0: [dict(text=base[i["id"]]) for i in DATA]}
    for sid in range(1, n_rep + 1):
        runs[sid] = run(sid)
    summary = {"n": len(DATA), "runs": {}, "pairwise_same_content": {}, "unstable_ids": []}
    for sid, outs in runs.items():
        rows = [instance_scores(parse_lenient(o["text"]), i["gold"]) for o, i in zip(outs, DATA)]
        a = aggregate(rows)
        summary["runs"][str(sid)] = dict(acc=a["acc"], fmt=sum(format_ok(o["text"]) for o in outs) / len(outs), failed_ids=[i["id"] for i, r in zip(DATA, rows) if not r["exact"]])
    for sid in range(1, n_rep + 1):
        same = [canon(runs[0][k]["text"]) == canon(runs[sid][k]["text"]) for k in range(len(DATA))]
        summary["pairwise_same_content"][f"0_vs_{sid}"] = sum(same) / len(same)
        summary["unstable_ids"] += [DATA[k]["id"] for k, s in enumerate(same) if not s]
    summary["unstable_ids"] = sorted(set(summary["unstable_ids"]))
    json.dump(summary, open(os.path.join(RES, "repro_check.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
