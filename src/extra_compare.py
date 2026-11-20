"""对 data/extra_unseen/ 的 3 个全新段落，跑 A / B / A2 / 本方案并存盘(无标注，人工对照原文判定)。"""
import json, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from pipeline import run_plain, run_spec
from prompts import MANUAL_A
from retrieval import ExampleStore, Glossary, load_jsonl
from scoring import format_ok, parse_lenient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rd = lambda n: open(os.path.join(ROOT, "prompts", n), encoding="utf-8").read()
SPEC = json.load(open(os.path.join(ROOT, "prompts", "std_kb_optimized_spec.json"), encoding="utf-8"))
store, gloss = ExampleStore(load_jsonl(os.path.join(ROOT, "data", "train.jsonl"))), Glossary()
cfg = {"A_manual": lambda i: run_plain(MANUAL_A, i), "B_direct_llm": lambda i: run_plain(rd("direct_llm.txt"), i),
       "A2_manual_schema": lambda i: run_plain(rd("manual_A2.txt"), i), "OURS": lambda i: run_spec(SPEC, i, gloss, store, repair=True)}
res = {}
for line in open(os.path.join(ROOT, "data", "extra_unseen", "extra_unseen.txt"), encoding="utf-8"):
    if not line.strip():
        continue
    uid, text = line.rstrip("\n").split("\t", 1)
    inst = dict(id=uid, text=text.strip())
    res[uid] = {}
    for name, fn in cfg.items():
        o = fn(inst); recs = parse_lenient(o["text"])
        res[uid][name] = dict(fmt_ok=format_ok(o["text"]), n_records=None if recs is None else len(recs),
                              records=None if recs is None else [{k: r.get(k) for k in ("material", "band_gap", "unit", "band_gap_eV", "method", "gap_type")} for r in recs if isinstance(r, dict)],
                              raw_head=o["text"][:160])
json.dump(res, open(os.path.join(ROOT, "results", "extra_compare.json"), "w"), ensure_ascii=False, indent=1)
for uid, d in res.items():
    print("=====", uid)
    for n, v in d.items():
        print(f"--- {n} fmt_ok={v['fmt_ok']} n={v['n_records']}")
        for r in v["records"] or []:
            print("   ", r["material"], r["band_gap"], r["unit"], r["band_gap_eV"], r["method"], r["gap_type"])
