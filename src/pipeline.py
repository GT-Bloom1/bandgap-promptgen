"""执行：给定方法与实例，调用目标模型，返回输出与 token 记账；含校验器驱动的修复重试。"""
from llm import TARGET_MODEL, call, pmap
from prompts import render_system, render_user
from retrieval import ExampleStore, Glossary
from verifier import verify

MAX_TOK = 1800


def run_plain(system, inst, model=None):
    r = call(model or TARGET_MODEL, system, "Paragraph:\n" + inst["text"] + "\n\nAnswer:", max_tokens=MAX_TOK)
    return dict(id=inst["id"], text=r["text"], in_tok=r["in_tok"], out_tok=r["out_tok"], calls=1, repaired=False, v_errors=[], v_warns=[])


def run_spec(spec, inst, glossary=None, store=None, k_gloss=6, k_shot=3, repair=False, loo=False, model=None):
    """spec 方法：glossary / store 为 None 时对应关闭知识注入 / few-shot；repair=True 时校验失败则带错误信息重试一次。"""
    system = render_system(spec)
    g = glossary.retrieve(inst["text"], k_gloss) if glossary else None
    ex = store.retrieve(inst["text"], k_shot, exclude_id=inst["id"] if loo else None) if store else None
    user = render_user(inst["text"], g, ex)
    m = model or TARGET_MODEL
    r = call(m, system, user, max_tokens=MAX_TOK)
    in_t, out_t, calls, repaired = r["in_tok"], r["out_tok"], 1, False
    text = r["text"]
    errs, warns = verify(inst["text"], text)
    first_errs, first_warns = list(errs), list(warns)
    if repair and (errs or warns):
        msg = "\n".join(["Errors:"] + [f"- {e}" for e in errs] + (["Warnings (re-check these values against the paragraph):"] + [f"- {w}" for w in warns] if warns else []))
        user2 = (user + "\n\nYour previous answer was:\n" + text + "\n\nAutomatic scientific verification found problems:\n" + msg +
                 "\n\nFix the answer. Remove records that are not band gaps of the studied material, correct wrong conversions, and keep everything that was correct. "
                 "A warning may be a false alarm: keep the value if the paragraph supports it. Return ONLY the corrected JSON array.")
        r2 = call(m, system, user2, max_tokens=MAX_TOK)
        in_t += r2["in_tok"]; out_t += r2["out_tok"]; calls += 1; repaired = True
        text = r2["text"]
    return dict(id=inst["id"], text=text, in_tok=in_t, out_tok=out_t, calls=calls, repaired=repaired,
                v_errors=first_errs, v_warns=first_warns)
