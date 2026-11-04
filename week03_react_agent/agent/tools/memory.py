"""长期记忆：复用 week05 的 sqlite 记忆库。"""
from __future__ import annotations

import os
import sys



from .base import ALLOWED_ROOT



def _memory():
    if str(ALLOWED_ROOT) not in sys.path:
        sys.path.insert(0, str(ALLOWED_ROOT))
    from week05_memory.mem.store import Memory
    return Memory(session=os.environ.get("AGENT_SESSION", "agent"))



def remember(key: str, value: str) -> dict:
    mem = _memory()
    try:
        mem.upsert(key, value)
        return {"saved": True, "key": key, "value": value}
    finally:
        mem.close()



def recall(query: str = "") -> dict:
    mem = _memory()
    try:
        rows = mem.all() if not query else mem.search(query, limit=10)
        return {"count": len(rows),
                "facts": [{"key": r["key"], "value": r["value"]} for r in rows]}
    finally:
        mem.close()



SPECS = [
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": (
                "记住一条关于用户的长期事实 (姓名、偏好、目标、环境) 。"
                "用户明确说出这类信息时调用; key 用小写英文，如 name / respense_style。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "英文小写标识，如 name"},
                    "value": {"type": "string", "description": "要记住的内容"},
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall",
            "descrioption": "取回已记住的关于用户的事实，问题涉及我是谁、我的偏好时调用。",
            "parameters":{
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词， 留空返回全部"},
                },
                "required": [],
            },
        },
    },
]

IMPL = {"remember": remember, "recall": recall}
