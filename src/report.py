"""汇总：表格(csv/json)、显著性检验、按障碍类别的准确率、图。"""
import csv, json, math, os, random, sys

sys.path.insert(0, os.path.dirname(__file__))
from scoring import aggregate, instance_scores_nomat, parse_lenient
from retrieval import load_jsonl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
rows = json.load(open(os.path.join(RES, "eval_rows.json")))
_gold = {i["id"]: i["gold"] for s_ in ("test", "hard") for i in load_jsonl(os.path.join(ROOT, "data", s_ + ".jsonl"))}
for _cfg in rows:   # 事后增加的名称无关指标: 只比数值/方法/gap_type
    for _r, _l in zip(rows[_cfg], open(os.path.join(RES, "outputs", _cfg + ".jsonl"), encoding="utf-8")):
        _o = json.loads(_l)
        _s = instance_scores_nomat(parse_lenient(_o["output"]), _gold[_r["id"]])
        _r.update(nm_exact=_s["exact"], nm_tp_full=_s["tp_full"], nm_n_pred=_s["n_pred"], nm_n_gold=_s["n_gold"], nm_tp_value=_s["tp_value"])
judge = json.load(open(os.path.join(RES, "judge_scores.json"))) if os.path.exists(os.path.join(RES, "judge_scores.json")) else {}
random.seed(0)

NAMES = {
    "A_manual": "A 人工 prompt", "B_direct_llm": "B 直接由 LLM 生成", "A2_manual_schema": "A2 人工+完整 schema 约束(参考上界)",
    "OURS": "本方案 (完整)", "OURS_noKB": "本方案 - 知识注入", "OURS_noLoop": "本方案 - 优化闭环", "OURS_noRepair": "本方案 - 校验修复",
    "COLD_gen_only": "冷启动: 仅生成器", "COLD_KB": "冷启动: +知识注入", "COLD_loop": "冷启动: +优化闭环",
    "COLD_full": "冷启动: 完整", "COLD_full_noRepair": "冷启动: 完整 - 校验修复"}


def metrics(rs):
    a = aggregate(rs)
    j = judge.get(NAMES_INV.get(rs[0]["_cfg"], ""), None) if False else None
    return a


def sub(cfg, split=None):
    return [r for r in rows[cfg] if split is None or r["split"] == split]


def summarize(cfg, split=None):
    rs = sub(cfg, split)
    a = aggregate(rs)
    n = len(rs)
    d = dict(n=n, acc=a["acc"], precision=a["precision"], recall=a["recall"], f1=a["f1"],
             fmt=sum(r["fmt_ok"] for r in rs) / n, tokens=sum(r["in_tok"] + r["out_tok"] for r in rs) / n,
             calls=sum(r["calls"] for r in rs) / n, repaired=sum(r["repaired"] for r in rs) / n)
    d["acc_nm"] = sum(r["nm_exact"] for r in rs) / n
    _tp, _np, _ng = (sum(r[k] for r in rs) for k in ("nm_tp_full", "nm_n_pred", "nm_n_gold"))
    _p, _r2 = _tp / _np if _np else 0, _tp / _ng
    d["f1_nm"] = 2 * _p * _r2 / (_p + _r2) if _p + _r2 else 0
    if cfg in judge:
        v = [judge[cfg][r["id"]] for r in rs if judge[cfg].get(r["id"]) is not None]
        d["judge"] = sum(v) / len(v) if v else None
    return d


def boot_diff(a, b, B=5000, key="exact"):
    """instance 级配对 bootstrap：返回 acc(a)-acc(b) 的均值与 95% CI。"""
    x = [r[key] for r in sub(a)]; y = [r[key] for r in sub(b)]
    n = len(x); ds = []
    for _ in range(B):
        idx = [random.randrange(n) for _ in range(n)]
        ds.append(sum(x[i] - y[i] for i in idx) / n)
    ds.sort()
    return sum(x) / n - sum(y) / n, ds[int(0.025 * B)], ds[int(0.975 * B)]


def mcnemar(a, b, key="exact"):
    """精确 McNemar(双侧二项)检验的 p 值，b01/b10 为不一致对数。"""
    x = [r[key] for r in sub(a)]; y = [r[key] for r in sub(b)]
    n10 = sum(1 for i, j in zip(x, y) if i and not j); n01 = sum(1 for i, j in zip(x, y) if j and not i)
    n = n10 + n01
    if n == 0:
        return 1.0, n10, n01
    k = min(n10, n01)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n * 2
    return min(1.0, p), n10, n01


PAIRS = [("OURS", "A_manual"), ("OURS", "B_direct_llm"), ("OURS", "A2_manual_schema"), ("OURS", "OURS_noKB"), ("OURS", "OURS_noLoop"), ("OURS", "OURS_noRepair"),
         ("COLD_full", "COLD_gen_only"), ("COLD_loop", "COLD_gen_only"), ("COLD_KB", "COLD_gen_only"), ("COLD_full", "COLD_full_noRepair")]


def main():
    out = {}
    with open(os.path.join(RES, "table_main.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["配置", "Test40 准确率(严格)", "Hard30 准确率(严格)", "合计70 准确率(严格)", "合计70 准确率(名称无关)", "记录级P(严格)", "记录级R(严格)", "记录级F1(严格)", "记录级F1(名称无关)",
                    "格式合规率", "专家评分代理(1-5)", "平均token/实例", "平均调用数/实例"])
        for cfg in rows:
            s_all, s_t, s_h = summarize(cfg), summarize(cfg, "test"), summarize(cfg, "hard")
            out[cfg] = dict(all=s_all, test=s_t, hard=s_h)
            w.writerow([NAMES[cfg], f"{s_t['acc']:.3f}", f"{s_h['acc']:.3f}", f"{s_all['acc']:.3f}", f"{s_all['acc_nm']:.3f}", f"{s_all['precision']:.3f}", f"{s_all['recall']:.3f}",
                        f"{s_all['f1']:.3f}", f"{s_all['f1_nm']:.3f}", f"{s_all['fmt']:.3f}", f"{s_all['judge']:.2f}" if s_all.get("judge") else "", f"{s_all['tokens']:.0f}", f"{s_all['calls']:.2f}"])
    sig = {}
    for a, b in PAIRS:
        rec = {}
        for key in ("exact", "nm_exact"):
            d, lo, hi = boot_diff(a, b, key=key)
            p, n10, n01 = mcnemar(a, b, key=key)
            rec[key] = dict(diff=d, ci=[lo, hi], p=p, a_only=n10, b_only=n01)
        sig[f"{a} vs {b}"] = rec
    out["_significance"] = sig
    tags = sorted({t for r in rows["OURS"] for t in r["tags"]})
    out["_by_tag"] = {cfg: {t: (sum(r["nm_exact"] for r in rows[cfg] if t in r["tags"]), sum(1 for r in rows[cfg] if t in r["tags"])) for t in tags} for cfg in rows}
    json.dump(out, open(os.path.join(RES, "summary.json"), "w"), ensure_ascii=False, indent=1)
    for cfg in rows:
        s = out[cfg]["all"]
        print(f"{NAMES[cfg]:32s} test={out[cfg]['test']['acc']:.3f} hard={out[cfg]['hard']['acc']:.3f} all={s['acc']:.3f} nm_all={s['acc_nm']:.3f} f1={s['f1']:.3f} f1nm={s['f1_nm']:.3f} fmt={s['fmt']:.3f} judge={s.get('judge')} tok={s['tokens']:.0f}")
    for k, v in sig.items():
        e, n = v["exact"], v["nm_exact"]
        print(f"{k:34s} strict {e['diff']:+.3f} [{e['ci'][0]:+.3f},{e['ci'][1]:+.3f}] p={e['p']:.3f} ({e['a_only']}/{e['b_only']}) | name-agnostic {n['diff']:+.3f} [{n['ci'][0]:+.3f},{n['ci'][1]:+.3f}] p={n['p']:.3f} ({n['a_only']}/{n['b_only']})")


if __name__ == "__main__":
    main()
