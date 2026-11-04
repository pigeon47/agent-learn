"""文件工具：读 / 列目录 / 写 (写只允许 scratch/)。"""
from __future__ import annotations

from .base import is_sensitive, safe_path, scratch_path



def read_file(path: str, max_chars: int = 3000) -> dict:
    p = safe_path(path)
    if is_sensitive(p):
        raise ValueError(f"拒绝读取敏感文件：{p.name}")
    if not p.is_file():
        raise ValueError(f"不是文件：{path}")
    text = p.read_text(encoding="utf-8", errors="replace")
    return {"path": str(p), "chars": len(text), "text": text[:max_chars]}



def list_dir(path: str = ".") -> dict:
    p = safe_path(path)
    if not p.is_dir():
        raise ValueError(f"不是目录：{path}")
    items = []
    for child in sorted(p.iterdir()):
        if is_sensitive(child):
            continue
        items.append({"name": child.name,
                      "type": "dir" if child.is_dir() else "file",
                      "size": child.stat().st_size if child.is_file() else 0})
        if len(items) >= 50:
            break
    return {"path": str(p), "count": len(items), "items": items}



def write_file(path: str, content: str) -> dict:
    if len(content) > 50000:
        raise ValueError(f"内容太长 (上限 5 万字符) ")
    p = scratch_path(path)
    if is_sensitive(p):
        raise ValueError(f"拒绝写入敏感文件名：{p.name}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"path": str(p), "chars": len(content)}



SPECS = [
    {
        "type": "function",
        "function": {                "name": "read_file",
            "description": "读取仓库内的文本文件内容，需要查看本地代码、笔记、配置是调用。",
            "parameters": {
                "type": "object",
                "properties": {                        "path": {"type": "string", "description": "相对仓库根的路径，或绝对路径"},
                    "max_chars": {"type": "integer", "description": "最多读多少字符，默认 3000"},
                },
                "required": ["path"],
            },
        },        
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "列出仓库内某个目录的文件与子目录。不确定文件在哪时先调用它。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "目录路径，默认仓库根 ."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description":(
                "把内容写成内容 (只能写 scratch/ 目录)。"
                "用户要求保存结果、生成报告、导出清单是调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "如 sratch/报告.md"},
                    "content": {"type": "string", "description": "文件内容"},
                },
                "required": ["path", "content"],
            },
        },
    },
]

IMPL = {"read_file": read_file, "list_dir": list_dir, "write_file": write_file}
