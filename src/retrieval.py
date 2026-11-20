"""知识注入（组件2）的检索部分：术语表关键词+TF-IDF 检索，few-shot 示例 TF-IDF 检索。"""
import json, os, re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


class Glossary:
    def __init__(self, path=os.path.join(ROOT, "kb", "glossary.json")):
        self.items = json.load(open(path, encoding="utf-8"))

    def retrieve(self, text, k=6):
        t = text.lower()
        scored = []
        for e in self.items:
            s = sum(1 for key in e["keys"] if key.lower() in t)
            if s:
                scored.append((s, e))
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:k]]


def _tok(s):
    return re.findall(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*|[^\sa-z0-9]", s.lower())


class ExampleStore:
    """few-shot 检索：对示例库段落建 TF-IDF，余弦相似度取 top-k。exclude_id 用于优化阶段留一，避免自己检索到自己。"""
    def __init__(self, examples):
        self.ex = examples
        self.vec = TfidfVectorizer(tokenizer=_tok, lowercase=False, ngram_range=(1, 2), sublinear_tf=True, token_pattern=None)
        self.mat = self.vec.fit_transform([e["text"] for e in examples])

    def retrieve(self, text, k=3, exclude_id=None):
        sims = cosine_similarity(self.vec.transform([text]), self.mat)[0]
        order = sorted(range(len(self.ex)), key=lambda i: -sims[i])
        out = [self.ex[i] for i in order if self.ex[i]["id"] != exclude_id]
        return out[:k]
