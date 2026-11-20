"""现场演示：对一段此前未见过的文本运行完整方案，并打印抽取结果与校验报告。
用法:
  python src/demo.py --demo-id D01            # 运行 data/demo.jsonl 里的样例(与训练/测试集互不重叠)
  python src/demo.py --text "段落..."          # 任意新段落
  python src/demo.py --file paragraph.txt
  python src/demo.py --all                    # 跑完全部 demo 样例并和标注对照"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from pipeline import run_spec
from retrieval import ExampleStore, Glossary, load_jsonl
from scoring import error_report, instance_scores, parse_lenient
from verifier import verify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = json.load(open(os.path.join(ROOT, "prompts", "std_kb_optimized_spec.json"), encoding="utf-8"))


def run_one(inst, store, gloss, verbose=True):
    out = run_spec(SPEC, inst, gloss, store, repair=True)
    recs = parse_lenient(out["text"])
    errs, warns = verify(inst["text"], out["text"])
    if verbose:
        print("段落:", inst["text"], "\n")
        print("检索到的术语条目:", [e["term"] for e in gloss.retrieve(inst["text"], 6)])
        print("检索到的示例:", [e["id"] for e in store.retrieve(inst["text"], 3)])
        print("\n抽取结果:")
        print(json.dumps(recs, ensure_ascii=False, indent=1) if recs is not None else out["text"])
        print(f"\n校验: errors={errs} warnings={warns}  (首轮校验问题 {len(out['v_errors'])+len(out['v_warns'])} 条, 触发修复重试={out['repaired']})")
        print(f"token: in={out['in_tok']} out={out['out_tok']} calls={out['calls']}")
    return out, recs, errs, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo-id"); ap.add_argument("--text"); ap.add_argument("--file"); ap.add_argument("--all", action="store_true"); ap.add_argument("--extra", action="store_true")
    a = ap.parse_args()
    store = ExampleStore(load_jsonl(os.path.join(ROOT, "data", "train.jsonl")))
    gloss = Glossary()
    demo = load_jsonl(os.path.join(ROOT, "data", "demo.jsonl"))
    if a.all:
        res = []
        for d in demo:
            print("=" * 100, d["id"])
            out, recs, errs, warns = run_one(d, store, gloss)
            sc = instance_scores(recs, d["gold"])
            print("与标注对照: 完全匹配" if sc["exact"] else "与标注差异: " + "; ".join(error_report(recs, d["gold"])))
            res.append(dict(id=d["id"], exact=sc["exact"], output=recs, errors=errs, warnings=warns, tokens=out["in_tok"] + out["out_tok"]))
        json.dump(res, open(os.path.join(ROOT, "results", "demo_outputs.json"), "w"), ensure_ascii=False, indent=1)
        print(f"\n演示集完全匹配 {sum(r['exact'] for r in res)}/{len(res)}")
        return
    if a.extra:  # data/extra_unseen/: 方案定稿之后才写入的 3 个全新段落，没有标注，输出由人工对照原文判定
        res = []
        for line in open(os.path.join(ROOT, "data", "extra_unseen", "extra_unseen.txt"), encoding="utf-8"):
            if not line.strip():
                continue
            uid, text = line.rstrip("\n").split("\t", 1)
            print("=" * 100, uid)
            out, recs, errs, warns = run_one(dict(id=uid, text=text.strip()), store, gloss)
            res.append(dict(id=uid, text=text.strip(), output=recs, errors=errs, warnings=warns, tokens=out["in_tok"] + out["out_tok"]))
        json.dump(res, open(os.path.join(ROOT, "results", "extra_unseen_outputs.json"), "w"), ensure_ascii=False, indent=1)
        return
    if a.demo_id:
        inst = next(d for d in demo if d["id"] == a.demo_id)
    else:
        text = a.text or (open(a.file, encoding="utf-8").read() if a.file else sys.stdin.read())
        inst = dict(id="adhoc", text=text.strip())
    run_one(inst, store, gloss)


if __name__ == "__main__":
    main()
