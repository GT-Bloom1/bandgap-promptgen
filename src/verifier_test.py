"""校验器自身的评测（不调用大模型）：
(1) 误报率：对人工标注的正确答案跑校验器，看会不会误报；
(2) 召回率：对正确答案注入 6 类科学性错误，看能否检出。输出 results/verifier_test.json"""
import copy, json, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
from retrieval import load_jsonl
from verifier import verify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
random.seed(1)
inst = [i for s in ("train", "test", "hard", "demo") for i in load_jsonl(os.path.join(ROOT, "data", s + ".jsonl"))]


def mutate(r, kind, paragraph):
    r = copy.deepcopy(r)
    if kind == "unit_as_ev":            # 单位写错: 把 nm 数值标成 eV(量纲错误)
        if r["unit"] not in ("nm", "um", "cm-1"): return None
        r["unit"] = "eV"; r["band_gap_eV"] = r["band_gap"]
    elif kind == "bad_conversion":      # 换算错误: eV 值乘 1.5
        r["band_gap_eV"] = round(r["band_gap_eV"] * 1.5, 3)
    elif kind == "out_of_range":        # 数量级错误: 100 倍
        r["band_gap"] = r["band_gap"] * 100; r["band_gap_eV"] = r["band_gap_eV"] * 100
    elif kind == "evidence_fabricated": # 证据链断裂: 改写原文片段
        r["evidence"] = "the measured gap of " + r["material"] + " is " + str(r["band_gap"]) + " " + r["unit"]
    elif kind == "bad_enum":            # 枚举非法
        r["method"] = "computed"
    elif kind == "wrong_value_vs_ref":  # 与文献值严重不符(但量纲合法、数字在证据里)
        if r["unit"] != "eV": return None
        v = round(r["band_gap"] * 3, 2)
        if v > 15: return None
        r["band_gap"] = v; r["band_gap_eV"] = v
        r["evidence"] = r["evidence"].replace(str(r["band_gap"] / 3), str(v))
        if str(v) not in r["evidence"]:
            r["evidence"] = r["evidence"] + f" ({v} eV)"      # 让证据检查通过，只考验参考值核查
        paragraph_ok = True
    return r


def main():
    kinds = ["unit_as_ev", "bad_conversion", "out_of_range", "evidence_fabricated", "bad_enum", "wrong_value_vs_ref"]
    # 误报
    fp_inst, fp_rec = [], 0
    for i in inst:
        errs, warns = verify(i["text"], json.dumps(i["gold"]))
        if errs or warns:
            fp_inst.append((i["id"], errs, warns))
    res = dict(clean_instances=len(inst), false_alarm_instances=len(fp_inst), false_alarms=[(a, b, c) for a, b, c in fp_inst])
    det = {}
    for k in kinds:
        n = hit = 0
        for i in inst:
            for ri, r in enumerate(i["gold"]):
                m = mutate(r, k, i["text"])
                if m is None: continue
                recs = [copy.deepcopy(x) for x in i["gold"]]; recs[ri] = m
                n += 1
                text = i["text"] if k != "wrong_value_vs_ref" else i["text"] + " " + m["evidence"]
                errs, warns = verify(text, json.dumps(recs))
                # 只计新增的告警: 与干净版本相比多出来的条目
                e0, w0 = verify(i["text"], json.dumps(i["gold"]))
                hit += int(len(errs) + len(warns) > len(e0) + len(w0))
        det[k] = dict(n=n, detected=hit, rate=round(hit / n, 3) if n else None)
    res["detection"] = det
    json.dump(res, open(os.path.join(ROOT, "results", "verifier_test.json"), "w"), ensure_ascii=False, indent=1)
    print("clean instances:", res["clean_instances"], "false alarm instances:", res["false_alarm_instances"])
    for a in res["false_alarms"]: print("  FA", a)
    for k, v in det.items(): print(f"{k:22s} n={v['n']:3d} detected={v['detected']:3d} rate={v['rate']}")


if __name__ == "__main__":
    main()
