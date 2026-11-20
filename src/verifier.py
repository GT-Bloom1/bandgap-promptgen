"""科学正确性校验（组件5）：单位量纲、数值范围、换算一致性、证据链、文献值一致性。
返回 (errors, warnings)。errors 触发修复重试；warnings 只在修复提示中提示复核。"""
import json, os, re

from scoring import FIELDS, GAPTYPES, METHODS, _elements, norm_mat, parse_lenient
from units import known_unit, norm_unit, to_ev

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = {k: v for k, v in json.load(open(os.path.join(ROOT, "kb", "reference_gaps.json"), encoding="utf-8")).items()
       if not k.startswith("_")}
EV_MIN, EV_MAX = 0.0, 15.0


def _num_in(text, x):
    """数值 x 是否以数字形式出现在 text 中（容忍千分位、小数末尾 0）。"""
    t = text.replace(",", "").replace("−", "-")
    nums = re.findall(r"\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", t)
    for s in nums:
        try:
            if abs(float(s) - float(x)) < 1e-9 * max(1, abs(float(x))):
                return True
        except ValueError:
            pass
    return False


_CONFINED = ("quantum dot", "nanocrystal", "nanowire", "nanosheet", "nanoparticle", "nanorod", "nanotube", "nanoribbon",
             "monolayer", "single-layer", "bilayer", "nanoplate", "qd", " nm)", "agnr", "amorphous", "a-si")


def _ref_range(material):
    """参考表只对体相材料核查：按化学式记号精确匹配(SnS 不会误配 SnS2)，
    量子点/纳米结构/单层等受尺寸与维度影响的材料不核查。"""
    m = str(material).lower()
    if any(w in m for w in _CONFINED):
        return None
    core = str(material).translate(str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")).split("(")[0]
    toks = {t for t in re.split(r"[^A-Za-z0-9.]+", core) if t} | {t for t in re.split(r"[^A-Za-z0-9.\-]+", core) if t}
    for k in REF:
        if k in toks:
            return REF[k]
    return None


def verify(paragraph, text):
    errors, warns = [], []
    recs = parse_lenient(text)
    if recs is None:
        return ["输出不是可解析的 JSON 数组"], warns
    for i, r in enumerate(recs):
        tag = f"第{i + 1}条"
        if not isinstance(r, dict):
            errors.append(f"{tag}: 不是对象"); continue
        miss = [k for k in FIELDS if k not in r]
        if miss:
            errors.append(f"{tag}: 缺少字段 {miss}"); continue
        if r["method"] not in METHODS:
            errors.append(f"{tag}: method={r['method']!r} 不在 {sorted(METHODS)}")
        if r["gap_type"] not in GAPTYPES:
            errors.append(f"{tag}: gap_type={r['gap_type']!r} 不在 {sorted(GAPTYPES)}")
        try:
            bg, ev = float(r["band_gap"]), float(r["band_gap_eV"])
        except Exception:
            errors.append(f"{tag}: band_gap/band_gap_eV 不是数值"); continue
        if not known_unit(str(r["unit"])):
            errors.append(f"{tag}: 单位 {r['unit']!r} 不在允许集合 eV/meV/nm/um/cm-1"); continue
        calc = to_ev(bg, r["unit"]) if bg != 0 else 0.0
        if abs(calc - ev) > max(0.01 * abs(calc), 0.002):
            errors.append(f"{tag}: 换算不一致，{bg} {r['unit']} 应为 {calc:.3f} eV，却写成 {ev}")
        if not (EV_MIN <= ev <= EV_MAX):
            errors.append(f"{tag}: band_gap_eV={ev} 超出物理合理范围 [{EV_MIN},{EV_MAX}] eV")
        ev_text = str(r["evidence"])
        if ev_text not in paragraph:
            errors.append(f"{tag}: evidence 不是原文的逐字子串")
        elif not _num_in(ev_text, bg):
            errors.append(f"{tag}: evidence 中没有出现数值 {r['band_gap']}")
        rng = _ref_range(str(r["material"]))
        if rng:
            lo, hi = rng
            if r["method"] == "experimental":
                ok = lo * 0.7 <= ev <= hi * 1.3
            else:  # 计算值允许系统性偏差(PBE 严重低估，GW/HSE 略高估)
                ok = 0.2 * lo <= ev <= 1.5 * hi
            if not ok:
                warns.append(f"{tag}: {r['material']} 的 {ev} eV 与文献参考范围 {lo}-{hi} eV 差距过大，请复核数值是否为该材料的带隙")
    return errors, warns
