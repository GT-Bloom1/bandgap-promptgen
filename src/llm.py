"""大模型调用封装：磁盘缓存(可离线复现)、token 记账、重试、线程并行。"""
import hashlib, json, os, threading, time
from concurrent.futures import ThreadPoolExecutor

import anthropic

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(ROOT, "cache")
TARGET_MODEL = os.environ.get("TARGET_MODEL", "claude-sonnet-5-5")      # 被测/被优化的模型
OPTIMIZER_MODEL = os.environ.get("OPTIMIZER_MODEL", "claude-sonnet-5-5")  # 生成器/反思器
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "claude-sonnet-5-5")          # 专家评分代理
OFFLINE = os.environ.get("OFFLINE", "0") == "1"   # 只读缓存，缓存未命中则报错

_client = None
_lock = threading.Lock()
_stats = {"calls": 0, "cache_hits": 0}


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(max_retries=3, timeout=180)
    return _client


def call(model, system, user, max_tokens=2000, temperature=0.0, sample_id=0):
    """返回 dict(text, in_tok, out_tok, cached)。相同参数命中缓存，token 数取首次真实调用的记录。"""
    key = hashlib.sha256(json.dumps([model, system, user, max_tokens, temperature, sample_id],
                                    ensure_ascii=False).encode()).hexdigest()
    path = os.path.join(CACHE_DIR, key[:2], key + ".json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            r = json.load(f)
        with _lock:
            _stats["cache_hits"] += 1
        return dict(text=r["text"], in_tok=r["in_tok"], out_tok=r["out_tok"], cached=True)
    if OFFLINE:
        raise RuntimeError("OFFLINE=1 且缓存未命中: " + key[:12])
    last = None
    for attempt in range(4):
        try:
            msg = _get_client().messages.create(
                model=model, max_tokens=max_tokens, system=system,
                messages=[{"role": "user", "content": user}],
                extra_body={"temperature": temperature})
            text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
            r = dict(text=text, in_tok=msg.usage.input_tokens, out_tok=msg.usage.output_tokens,
                     model=model, system=system, user=user, temperature=temperature, sample_id=sample_id)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(r, f, ensure_ascii=False)
            with _lock:
                _stats["calls"] += 1
            return dict(text=text, in_tok=r["in_tok"], out_tok=r["out_tok"], cached=False)
        except Exception as e:  # 限流/网络错误：退避重试
            last = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"LLM 调用失败: {last}")


def pmap(fn, items, workers=6):
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(fn, items))


def stats():
    return dict(_stats)
