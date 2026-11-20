"""失败案例与校验器分析（供报告引用）。"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from retrieval import load_jsonl
from scoring import error_report, parse_lenient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data = {i["id"]: i for s in ("test", "hard") for i in load_jsonl(os.path.join(ROOT, "data", s + ".jsonl"))}


def load(cfg):
    return [json.loads(l) for l in open(os.path.join(ROOT, "results", "outputs", cfg + ".jsonl"), encoding="utf-8")]


def show(cfg, ids=None, maxlen=500):
    for r in load(cfg):
        if r["exact"] or (ids and r["id"] not in ids):
            continue
        i = data[r["id"]]
        print(f"--- [{cfg}] {r['id']} tags={i['tags']} fmt_ok={r['fmt_ok']}")
        print("TEXT:", i["text"][:350])
        p = parse_lenient(r["output"])
        for l in (error_report(p, i["gold"]) if p is not None else ["不可解析"]):
            print("   *", l)
        print("   v_errors:", r.get("v_errors"), "v_warns:", r.get("v_warns"))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "show":
        show(sys.argv[2], sys.argv[3].split(",") if len(sys.argv) > 3 else None)
    if cmd == "verifier":
        for cfg in ("OURS_noRepair", "A2_manual_schema", "A_manual"):
            rs = load(cfg)
            flag = [r for r in rs if r["v_errors"] or r["v_warns"]]
            wrong = [r for r in rs if not r["exact"]]
            tp = [r for r in flag if not r["exact"]]
            print(cfg, "flagged", len(flag), "wrong", len(wrong), "flagged&wrong", len(tp), "ids flagged", [r["id"] for r in flag])
        rs = load("OURS"); print("OURS repaired:", [(r["id"], r["exact"]) for r in rs if r["repaired"]])
