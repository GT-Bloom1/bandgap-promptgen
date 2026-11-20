"""优化闭环（组件4）：生成 -> 执行 -> 评价 -> 反思 -> 改写。
OPRO/TextGrad 式：用训练集上的失败样例(含标注差异)做"文本梯度"，让优化器 LLM 改写规则与自检清单；
每轮采样 N 个候选，在训练集上实际执行并打分，保留最优；连续无提升则早停。"""
import copy, json

from llm import OPTIMIZER_MODEL, TARGET_MODEL, call, pmap
from pipeline import run_spec
from scoring import aggregate, error_report, instance_scores, parse_lenient

REFLECT_SYSTEM = "You are an expert prompt optimizer for scientific information extraction. Reply with a single JSON object only."
REFLECT_USER = """You are improving the instruction part of an LLM prompt that extracts band gap records from materials-science paragraphs.

CURRENT PROMPT COMPONENTS
role: {role}
rules:
{rules}
self_check:
{checks}

SCORE HISTORY (train set, higher is better; score = (exact-match accuracy + record F1)/2):
{history}

FAILURES OF THE CURRENT PROMPT ON THE TRAIN SET (paragraph, gold answer, model answer, differences):
{failures}

Task: rewrite the components so that these kinds of errors disappear without breaking cases that already work.
Requirements:
- Each rule must be general and actionable (a decision criterion), at most 40 words. Never mention a specific material, number or paragraph from the failures.
- At most {max_rules} rules and {max_checks} self_check items. Merge or delete redundant or counter-productive items.
- Keep the output format unchanged (it is handled elsewhere).
Return JSON: {{"role": str, "rules": [str], "self_check": [str], "analysis": "one or two sentences naming the error patterns you addressed"}}"""


def evaluate_spec(spec, train, glossary, store, repair=False):
    """在训练集上执行并评价。leave-one-out 检索，避免示例库里检索到自己。"""
    outs = pmap(lambda i: run_spec(spec, i, glossary, store, repair=repair, loo=True), train)
    scs = [instance_scores(parse_lenient(o["text"]), i["gold"]) for o, i in zip(outs, train)]
    agg = aggregate(scs)
    toks = sum(o["in_tok"] + o["out_tok"] for o in outs)
    return dict(score=(agg["acc"] + agg["f1"]) / 2, agg=agg, outs=outs, scs=scs, tokens=toks)


def _failures_text(train, outs, scs, k=8):
    bad = [(i, o, s) for i, o, s in zip(train, outs, scs) if not s["exact"]]
    bad.sort(key=lambda x: -(x[2]["n_gold"] - x[2]["tp_full"] + abs(x[2]["n_pred"] - x[2]["n_gold"])))
    chunks = []
    for i, o, s in bad[:k]:
        pred = parse_lenient(o["text"])
        diffs = error_report(pred, i["gold"]) if pred is not None else ["输出无法解析为 JSON 数组"]
        keys = ("material", "band_gap", "unit", "band_gap_eV", "method", "gap_type")
        gold_short = [{k_: g[k_] for k_ in keys} for g in i["gold"]]
        pred_short = [{k_: p.get(k_) for k_ in keys} for p in (pred or []) if isinstance(p, dict)]
        chunks.append(f"Paragraph: {i['text']}\nGold: {json.dumps(gold_short, ensure_ascii=False)}\nModel: {json.dumps(pred_short, ensure_ascii=False)}\nDifferences: " + "; ".join(diffs))
    return ("\n---\n".join(chunks) if chunks else "(none)"), len(bad)


def propose(spec, history, failures, sample_id, max_rules=12, max_checks=8):
    user = REFLECT_USER.format(
        role=spec["role"], rules="\n".join(f"{i + 1}. {r}" for i, r in enumerate(spec["rules"])) or "(none)",
        checks="\n".join(f"- {c}" for c in spec["self_check"]) or "(none)",
        history="\n".join(f"round {h['round']}: score {h['score']:.3f} (acc {h['acc']:.3f}, f1 {h['f1']:.3f}), {h['n_rules']} rules" for h in history),
        failures=failures, max_rules=max_rules, max_checks=max_checks)
    r = call(OPTIMIZER_MODEL, REFLECT_SYSTEM, user, max_tokens=3000, temperature=1.0, sample_id=sample_id)
    t = r["text"]
    new = json.loads(t[t.find("{"): t.rfind("}") + 1])
    out = copy.deepcopy(spec)
    out["role"] = new.get("role", spec["role"])
    out["rules"] = [str(x) for x in new["rules"]][:max_rules]
    out["self_check"] = [str(x) for x in new.get("self_check", spec["self_check"])][:max_checks]
    out["analysis"] = new.get("analysis", "")
    return out, r["in_tok"] + r["out_tok"]


def optimize(spec0, train, glossary, store, rounds=5, n_cand=3, patience=2, log=print):
    """返回 (best_spec, info)。info.trace 记录每轮得分，供报告画收敛曲线。"""
    cur = spec0
    ev = evaluate_spec(cur, train, glossary, store)
    trace = [dict(round=0, score=ev["score"], acc=ev["agg"]["acc"], f1=ev["agg"]["f1"], n_rules=len(cur["rules"]), kind="init", analysis="")]
    opt_tokens = ev["tokens"]; opt_calls = len(train)
    stall = 0
    log(f"[round 0] score={ev['score']:.3f} acc={ev['agg']['acc']:.3f} f1={ev['agg']['f1']:.3f}")
    for rd in range(1, rounds + 1):
        if ev["agg"]["acc"] == 1.0 and ev["agg"]["f1"] == 1.0:
            log("train 已满分，停止"); break
        failures, nbad = _failures_text(train, ev["outs"], ev["scs"])
        cands = []
        for c in range(n_cand):
            try:
                cand, tk = propose(cur, trace, failures, sample_id=rd * 10 + c)
            except Exception as e:
                log(f"  candidate {c} 解析失败: {e}"); continue
            opt_tokens += tk
            cev = evaluate_spec(cand, train, glossary, store)
            opt_tokens += cev["tokens"]; opt_calls += len(train)
            cands.append((cev["score"], -len(cand["rules"]), cand, cev))
            log(f"  [round {rd}] cand {c}: score={cev['score']:.3f} acc={cev['agg']['acc']:.3f} f1={cev['agg']['f1']:.3f} rules={len(cand['rules'])}")
        if not cands:
            break
        cands.sort(key=lambda x: (x[0], x[1]), reverse=True)
        best = cands[0]
        improved = best[0] > ev["score"] + 1e-9
        trace.append(dict(round=rd, score=best[0], acc=best[3]["agg"]["acc"], f1=best[3]["agg"]["f1"], n_rules=len(best[2]["rules"]),
                          kind="accepted" if improved else "rejected", analysis=best[2].get("analysis", ""),
                          cand_scores=[round(c[0], 3) for c in cands], train_failures_before=nbad))
        if improved:
            cur, ev, stall = best[2], best[3], 0
            log(f"[round {rd}] 接受: score={best[0]:.3f}")
        else:
            stall += 1
            log(f"[round {rd}] 无提升，保留旧版本 (stall={stall})")
            if stall >= patience:
                break
    cur = dict(cur); cur.pop("analysis", None)
    return cur, dict(trace=trace, opt_tokens=opt_tokens, opt_calls=opt_calls, final_train=dict(ev["agg"]))
