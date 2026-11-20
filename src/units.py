"""单位换算：所有带隙值统一换算为 eV（hc = 1239.841984 eV·nm）。"""
HC_EV_NM = 1239.841984

# 单位 -> 换算函数（输入数值，返回 eV）
_CONV = {
    "ev": lambda x: x,
    "mev": lambda x: x / 1000.0,
    "nm": lambda x: HC_EV_NM / x,
    "um": lambda x: HC_EV_NM / (x * 1000.0),
    "cm-1": lambda x: x * HC_EV_NM * 1e-7,   # 1 cm^-1 = 1.239842e-4 eV
    "j": lambda x: x / 1.602176634e-19,
}


def norm_unit(u: str) -> str:
    u = (u or "").strip().lower().replace("μ", "u").replace("µ", "u")
    u = u.replace("−", "-").replace("⁻¹", "-1").replace("cm^-1", "cm-1").replace("cm−1", "cm-1")
    u = u.replace("wavenumber", "cm-1").replace(" ", "")
    return {"electronvolt": "ev", "electronvolts": "ev", "micron": "um", "microns": "um",
            "umeter": "um", "μm": "um"}.get(u, u)


def known_unit(u: str) -> bool:
    return norm_unit(u) in _CONV


def to_ev(value: float, unit: str) -> float:
    return _CONV[norm_unit(unit)](float(value))
