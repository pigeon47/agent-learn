"""工具包：汇总模块 → TOOLS / TOOL_IMPL / call_tool。"""
from __future__ import annotations

import json

from . import basic, code, files, media, memory, notes, web

_MODULES = (basic, code, files, media, memory, notes, web)


TOOLS = [spec for module in _MODULES for spec in module.SPECS]
TOOL_IMPL = {name: fn for module in _MODULES for name, fn in module.IMPL.items()}



def call_tool(name: str, arguments: dict) -> tuple[bool, str]:
    fn = TOOL_IMPL.get(name)
    if fn is None:
        return False,f"未知工具：{name}。可用工具：{",".join(TOOL_IMPL)}"
    try:
        result = fn(**arguments)
        return True,json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return False,f"{type(exc).__name__}: {exc}"