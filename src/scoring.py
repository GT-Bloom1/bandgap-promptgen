"""输出解析与评分：格式合规率、记录级/实例级准确率。"""
import json, re

from units import known_unit, norm_unit, to_ev

FIELDS = ["material", "band_gap", "unit", "band_gap_eV", "method", "gap_type", "evidence"]
METHODS = {"experimental", "DFT", "other_calc"}
GAPTYPES = {"optical", "electronic", "unspecified"}

_SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def norm_mat(s):
    s = str(s).translate(_SUB).lower()
    return re.sub(r"[^a-z0-9]", "", s)


_ELEMENTS = set("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu".split())
_FORMULA_TOKEN = re.compile(r"^(?:[A-Z][a-z]?(?:\d+(?:\.\d+)?)?)+$")


def _elements(material):
    """取括号前的名称部分里的化学式记号，返回元素集合；没有化学式记号则返回 None。"""
    core = str(material).translate(_SUB).split("(")[0] or str(material)
    els = set()
    for tok in re.split(r"[^A-Za-z0-9.]+", core):
        if tok and _FORMULA_TOKEN.match(tok):
            syms = re.findall(r"[A-Z][a-z]?", tok)
            if all(s in _ELEMENTS for s in syms):
                els.update(syms)
    return els or None


def same_material(a, b):
    """材料名匹配：优先比较元素集合(一方包含另一方，容忍掺杂/相/尺寸描述差异)；无化学式时退回规范化字符串包含。"""
    ea, eb = _elements(a), _elements(b)
    if ea and eb:
        return ea <= eb or eb <= ea
    na, nb = norm_mat(a), norm_mat(b)
    return bool(na) and bool(nb) and (na in nb or nb in na)


def parse_strict(text):
    """严格：整个输出必须就是一个 JSON 数组（不允许代码围栏、前后说明文字）。"""
    try:
        v = json.loads(text.strip())
        return v if isinstance(v, list) else None
    except Exception:
        return None


def parse_lenient(text):
    """宽松：剥掉代码围栏与说明文字，取第一个完整的 JSON 数组。用于计算准确率，使格式问题与内容问题分开统计。"""
    v = parse_strict(text)
    if v is not None:
        return v
    t = re.sub(r"```(?:json)?", "", text)
    start = t.find("[")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(t)):
            c = t[i]
            if in_str:
                if esc: esc = False
                elif c == "\\": esc = True
                elif c == '"': in_str = False
            else:
                if c == '"': in_str = True
                elif c == "[": depth += 1
                elif c == "]":
                    depth -= 1
                    if depth == 0:
                        try:
                            v = json.loads(t[start:i + 1])
                            if isinstance(v, list):
                                return v
                        except Exception:
                            pass
                        break
        start = t.find("[", start + 1)
    return None


def schema_ok(rec):
    """单条记录是否满足 schema（字段齐全、类型和枚举合法）。"""
    if not isinstance(rec, dict) or any(k not in rec for k in FIELDS):
        return False
    try:
        float(rec["band_gap"]); float(rec["band_gap_eV"])
    except Exception:
        return False
    return (isinstance(rec["material"], str) and isinstance(rec["unit"], str)
            and rec["method"] in METHODS and rec["gap_type"] in GAPTYPES
            and isinstance(rec["evidence"], str))


def format_ok(text):
    """格式合规：严格 JSON 数组且每条记录符合 schema。"""
    v = parse_strict(text)
    return v is not None and all(schema_ok(r) for r in v)


def _val(r):
    try:
        return float(r["band_gap_eV"])
    except Exception:
        return None


def _tol(g):
    return max(0.02, 0.01 * g)


def match(pred, gold):
    """贪心二部匹配：先按 (材料名包含 + eV 数值在容差内) 配对，再看 method / gap_type 是否也对。
    返回 dict(tp_full, tp_value, n_pred, n_gold, pairs)。"""
    pred = [p for p in (pred or []) if isinstance(p, dict)]
    used, pairs = set(), []
    for gi, g in enumerate(gold):
        best, bd = None, 1e9
        for pi, p in enumerate(pred):
            if pi in used:
                continue
            pv = _val(p)
            if pv is None or not same_material(g["material"], p.get("material", "")):
                continue
            d = abs(pv - g["band_gap_eV"])
            if d <= _tol(g["band_gap_eV"]) and d < bd:
                best, bd = pi, d
        if best is not None:
            used.add(best)
            pairs.append((gi, best))
    tp_val = len(pairs)
    tp_full = sum(1 for gi, pi in pairs
                  if pred[pi].get("method") == gold[gi]["method"] and pred[pi].get("gap_type") == gold[gi]["gap_type"])
    return dict(tp_full=tp_full, tp_value=tp_val, n_pred=len(pred), n_gold=len(gold), pairs=pairs, pred=pred)


def instance_scores(pred, gold):
    m = match(pred, gold)
    exact = int(pred is not None and m["tp_full"] == len(gold) and m["n_pred"] == len(gold))
    return dict(exact=exact, tp_full=m["tp_full"], tp_value=m["tp_value"],
                n_pred=m["n_pred"] if pred is not None else 0, n_gold=len(gold))


def aggregate(rows):
    """rows: instance_scores 列表 -> 汇总指标。"""
    n = len(rows)
    tp = sum(r["tp_full"] for r in rows); tv = sum(r["tp_value"] for r in rows)
    npred = sum(r["n_pred"] for r in rows); ngold = sum(r["n_gold"] for r in rows)
    def prf(t):
        p = t / npred if npred else 0.0
        r_ = t / ngold if ngold else 0.0
        return p, r_, (2 * p * r_ / (p + r_) if p + r_ else 0.0)
    p, r_, f1 = prf(tp); pv, rv, fv = prf(tv)
    return dict(acc=sum(r["exact"] for r in rows) / n, precision=p, recall=r_, f1=f1, value_f1=fv)


def error_report(pred, gold):
    """给反思器看的差异摘要：漏抽、多抽、字段错误。"""
    m = match(pred, gold)
    pairs = {gi: pi for gi, pi in m["pairs"]}
    pi_used = set(pairs.values())
    lines = []
    for gi, g in enumerate(gold):
        if gi not in pairs:
            lines.append(f"漏抽/数值错误: 应有 {g['material']} {g['band_gap_eV']} eV ({g['method']}, {g['gap_type']})")
        else:
            p = m["pred"][pairs[gi]]
            if p.get("method") != g["method"]:
                lines.append(f"method 错误: {g['material']} {g['band_gap_eV']} eV 应为 {g['method']}，模型给 {p.get('method')}")
            if p.get("gap_type") != g["gap_type"]:
                lines.append(f"gap_type 错误: {g['material']} {g['band_gap_eV']} eV 应为 {g['gap_type']}，模型给 {p.get('gap_type')}")
    for pi, p in enumerate(m["pred"]):
        if pi not in pi_used:
            lines.append(f"多抽/数值错误: 模型输出了 {p.get('material')} {p.get('band_gap')} {p.get('unit')} (={p.get('band_gap_eV')} eV)，标注中没有")
    return lines


def match_nomat(pred, gold):
    """名称无关匹配：只按 eV 数值(容差内)配对，再比 method / gap_type。
    用于排除“模型把 h-BN 写成 Hexagonal boron nitride”这类命名差异造成的假失败。"""
    pred = [p for p in (pred or []) if isinstance(p, dict)]
    used, pairs = set(), []
    for gi, g in enumerate(gold):
        best, bd = None, 1e9
        for pi, p in enumerate(pred):
            pv = _val(p)
            if pi in used or pv is None:
                continue
            d = abs(pv - g["band_gap_eV"])
            if d <= _tol(g["band_gap_eV"]) and d < bd:
                best, bd = pi, d
        if best is not None:
            used.add(best); pairs.append((gi, best))
    tp_full = sum(1 for gi, pi in pairs if pred[pi].get("method") == gold[gi]["method"] and pred[pi].get("gap_type") == gold[gi]["gap_type"])
    return dict(tp_full=tp_full, tp_value=len(pairs), n_pred=len(pred), n_gold=len(gold))


def instance_scores_nomat(pred, gold):
    m = match_nomat(pred, gold)
    exact = int(pred is not None and m["tp_full"] == len(gold) and m["n_pred"] == len(gold))
    return dict(exact=exact, tp_full=m["tp_full"], tp_value=m["tp_value"], n_pred=m["n_pred"] if pred is not None else 0, n_gold=len(gold))
