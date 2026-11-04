"""知识库检索：复用：week04的BM25索引。"""
from __future__ import annotations

import sys

from .base import ALLOWED_ROOT

index_cache = None



def _get_index():
    global index_cache
    if index_cache is None:
        if str(ALLOWED_ROOT) not in sys.path:
            sys.path.insert(0, str(ALLOWED_ROOT))
        from week04_rag.rag.chunking import load_corpus
        from week04_rag.rag.index import BM25
        index_cache = BM25(load_corpus(size=512))
    return index_cache



def search_notes(query: str, top_k: int = 3) -> dict:
    index = _get_index()
    hits = index.search(query, top_k=top_k, drop_stopwords=True)
    return {"query": query, "count": len(hits),
            "hits": [{"score": round(s, 2), "doc": c["doc"],
                     "heading": c["heading"], "text": c["text"][:600]}
                     for s, c in hits]}



SPECS = [
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": (
                "在本地笔记里搜索相关段落 (BM25) 。问题涉及 asyncio 用法、"
                "AI Agent 学习路线等本地资料时优先用它，比互联网更快更准。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "问题或关键词"},
                    "top_k": {"type": "integer", "description": "返回几段，默认 3"},
                },
                "required": ["query"],
            },
        },
    },
]

IMPL = {"search_notes": search_notes}