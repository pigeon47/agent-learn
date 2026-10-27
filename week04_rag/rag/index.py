"""极简 BM25：中文按「单字 + 双字 bigram」切分，英文数字按词。零依赖。

为什么中文要 bigram：
    中文没有空格，按词切需要词典（jieba）。用「字 + 相邻双字」做特征既不用词典，
    又能捕捉「检索」「事件循环」这类组合，是工程上很实用的一招。
"""
from __future__ import annotations

import math
import re
from collections import Counter

_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]+|\d+(?:\.\d+)?|[\u4e00-\u9fff]+")

# 中文功能词：几乎每个块都有，对排序只有干扰没有贡献。
# 加入它们是「最便宜的检索质量改进」，实测能把 Q1 的 top-1 从错误文档纠正回来。
STOPWORDS = set(
    "的 了 是 在 和 与 用 怎么 什么 如何 为什么 吗 呢 有 要 可以 这 那 个 一 也 就 都 我 你 他".split()
)


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for m in _WORD.finditer(text):
        s = m.group()
        if "\u4e00" <= s[0] <= "\u9fff":
            tokens.extend(s)                                      # 单字
            tokens.extend(s[i:i + 2] for i in range(len(s) - 1))  # 双字
        else:
            tokens.append(s.lower())
    return tokens


class BM25:
    """经典 BM25：score = Σ idf * tf*(k1+1) / (tf + k1*(1-b+b*dl/avgdl))"""

    def __init__(self, docs: list[dict], text_key: str = "text",
                 k1: float = 1.5, b: float = 0.75) -> None:
        self.docs = docs
        self.k1, self.b = k1, b
        self.tfs = [Counter(tokenize(d[text_key])) for d in docs]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avg_len = sum(self.lens) / max(len(self.lens), 1)
        self.df: Counter = Counter()
        for tf in self.tfs:
            self.df.update(tf.keys())
        self.N = len(docs)

    def _idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log(1 + (self.N - df + 0.5) / (df + 0.5))

    def analyze_query(self, query: str) -> dict:
        """分析查询词元在库里的覆盖情况，供拒答判断使用。

        known   ：库里有、且不是停用词的词元（真正参与打分的）
        missing ：库里完全没有的词元（关键实体缺失的信号）
        stopwords：被判为功能词的词元
        """
        toks = tokenize(query)
        known = [t for t in toks if self.df.get(t, 0) > 0 and t not in STOPWORDS]
        missing = [t for t in toks if self.df.get(t, 0) == 0]
        stop = [t for t in toks if t in STOPWORDS]
        return {"known": known, "missing": missing, "stopwords": stop}

    def search(self, query: str, top_k: int = 5,
               drop_stopwords: bool = True) -> list[tuple[float, dict]]:
        """返回 [(score, chunk), ...]，按分数降序。

        drop_stopwords=True 时先过滤停用词与库中不存在的词元，再做 BM25 打分。
        """
        terms = [t for t in tokenize(query) if self.df.get(t, 0) > 0]
        if drop_stopwords:
            terms = [t for t in terms if t not in STOPWORDS]
        if not terms:
            return []

        q = Counter(terms)
        scored: list[tuple[float, dict]] = []
        for i, tf in enumerate(self.tfs):
            score = 0.0
            for term, qn in q.items():
                f = tf.get(term, 0)
                if not f:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * self.lens[i] / (self.avg_len or 1))
                score += self._idf(term) * f * (self.k1 + 1) / denom * qn
            if score > 0:
                scored.append((score, self.docs[i]))
        scored.sort(key=lambda x: -x[0])
        return scored[:top_k]


if __name__ == "__main__":
    from .chunking import load_corpus

    chunks = load_corpus(size=512)
    index = BM25(chunks)
    print(f"索引完成：{len(chunks)} 块，平均长度 {int(index.avg_len)} 词元\n")

    queries = [
        "asyncio 的 gather 怎么用",                    # 期望 asyncio函数速查手册
        "DeepSeek 思考模式下 temperature 还有效吗",      # 期望 agent学习路线
        "怎么用 Kubernetes 部署服务",                   # 两份文档都没提 -> 观察拒答信号
    ]
    for query in queries:
        info = index.analyze_query(query)
        print(f"=== 查询：{query}")
        print(f"  参与打分={info['known']}")
        print(f"  库中缺失={info['missing']}")
        print(f"  停用词  ={info['stopwords']}")
        for label, flag in (("过滤前", False), ("过滤后", True)):
            hits = index.search(query, top_k=2, drop_stopwords=flag)
            print(f"  {label}:")
            if not hits:
                print("    （无命中）")
            for score, c in hits:
                print(f"    {score:6.2f}  {c['chunk_id']:24s} {c['doc']} | {c['heading']}")
        print()
