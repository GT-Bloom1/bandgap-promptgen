"""导出失败案例当时实际发给模型的提示词(系统提示词 + 用户消息),并验证与缓存中的真实请求一致。
用法: python3 src/dump_failure_prompts.py   输出 results/failure_prompts.json"""
import hashlib, json, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from llm import CACHE_DIR, TARGET_MODEL
from pipeline import MAX_TOK
from prompts import manual_a2_system, render_system, render_user
from retrieval import ExampleStore, Glossary, load_jsonl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
jl = lambda n: load_jsonl(os.path.join(ROOT, "data", n + ".jsonl"))
TRAIN, DATA = jl("train"), {r["id"]: r for r in jl("test") + jl("hard")}
GLOSS, STORE = Glossary(), ExampleStore(TRAIN)
spec = lambda n: json.load(open(os.path.join(ROOT, "prompts", n + ".json"), encoding="utf-8"))

# (案例, 配置, 实例, 系统提示词文件, 是否检索术语与示例)
CASES = [("案例 1", "OURS", "X07", "std_kb_optimized_spec", True), ("案例 2", "OURS", "X52", "std_kb_optimized_spec", True),
         ("案例 3a", "OURS", "X11", "std_kb_optimized_spec", True), ("案例 3b", "OURS", "X38", "std_kb_optimized_spec", True),
         ("案例 4", "OURS_noKB", "X66", "std_nokb_optimized_spec", False), ("案例 5", "COLD_loop", "X19", "cold_nokb_optimized_spec", False),
         ("案例 6", "COLD_KB", "X18", "cold_initial_spec", True), ("案例 7", "A2_manual_schema", "X41", "manual_A2", None)]


def key(system, user):
    return hashlib.sha256(json.dumps([TARGET_MODEL, system, user, MAX_TOK, 0.0, 0], ensure_ascii=False).encode()).hexdigest()


out = []
for no, cfg, iid, sysname, kb in CASES:
    text = DATA[iid]["text"]
    if kb is None:
        system, user = manual_a2_system(), "Paragraph:\n" + text + "\n\nAnswer:"
    else:
        system = render_system(spec(sysname))
        user = render_user(text, GLOSS.retrieve(text, 6) if kb else None, STORE.retrieve(text, 3) if kb else None)
    k = key(system, user)
    hit = os.path.exists(os.path.join(CACHE_DIR, k[:2], k + ".json"))
    out.append(dict(case=no, config=cfg, id=iid, system_name=sysname, system=system, user=user, matches_cached_request=hit))
    print(no, cfg, iid, "缓存命中(与真实请求一致):", hit)
json.dump(out, open(os.path.join(ROOT, "results", "failure_prompts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
