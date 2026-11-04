r"""week03 工具链自检。

用法（在 week03_react_agent 目录下）：
    E:\agent-learn\env\python.exe check_tools.py
    E:\agent-learn\env\python.exe check_tools.py --live     # 额外跑两条端到端（花 token）

只读检查，不调用 LLM（--live 除外）。
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT))

from agent.tools import TOOLS, TOOL_IMPL, call_tool   # noqa: E402

results: list[bool] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    results.append(cond)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


def smoke(name: str, args: dict, want_ok: bool = True) -> str:
    ok, text = call_tool(name, args)
    check(f"{name} {'已成功' if want_ok else '未成功'}", ok == want_ok, str(text)[:90])
    return text


# ---------------------------------------------------------------- 1. 结构
print("\n=== 1. 结构 ===")
check("工具数 == 13", len(TOOL_IMPL) == 13, f"{len(TOOL_IMPL)} 个")
check("TOOLS 与 TOOL_IMPL 名字一致",
      {s["function"]["name"] for s in TOOLS} == set(TOOL_IMPL),
      f"TOOLS={len(TOOLS)} IMPL={len(TOOL_IMPL)}")
for mod in ("basic", "web", "files", "code", "media", "notes", "memory"):
    m = importlib.import_module(f"agent.tools.{mod}")
    sp, im = len(m.SPECS), len(m.IMPL)
    check(f"{mod}: SPECS == IMPL", sp == im, f"{sp}/{im}")

# ---------------------------------------------------------------- 2. 基础工具
print("\n=== 2. 基础工具 ===")
smoke("get_time", {})
text = smoke("calculator", {"expression": "3**7*2"})
check("calculator 结果正确", json.loads(text).get("value") == 4374, text[:40])
text = smoke("python_exec", {"code": "print(sum(range(11)))"})
check("python_exec stdout 正确", json.loads(text).get("stdout", "").strip() == "55", text[:60])
text = smoke("get_weather", {"city": "北京"})
w = json.loads(text) if text.startswith("{") else {}
check("天气 temp_c 是数字", isinstance(w.get("temp_c"), (int, float)), str(w.get("temp_c")))
check("天气 region 非空", bool(w.get("region")), repr(w.get("region")))

# ---------------------------------------------------------------- 3. 文件工具
print("\n=== 3. 文件工具 ===")
text = smoke("list_dir", {"path": "."})
check("list_dir 返回多项", json.loads(text).get("count", 0) > 1, text[:60])
smoke("read_file", {"path": "week03_react_agent/agent/loop.py", "max_chars": 60})
smoke("write_file", {"path": "scratch/_selfcheck.md", "content": "# selfcheck ok"})

print("\n=== 4. 安全边界（三条都必须被拒）===")
smoke("write_file", {"path": "week04_rag/x.md", "content": "no"}, want_ok=False)
smoke("read_file", {"path": "C:/Windows/win.ini"}, want_ok=False)
text = smoke("python_exec", {"code": "import os; print(os.environ.get('DEEPSEEK_API_KEY'))"})
check("子进程里读不到 API Key", "sk-" not in text, text[:70])

# ---------------------------------------------------------------- 5. 联网与检索
print("\n=== 5. 联网与检索 ===")
text = smoke("web_search", {"query": "asyncio gather 异常", "max_results": 2})
if text.startswith("{"):
    urls = [x["url"] for x in json.loads(text)["results"]]
    bad = [u for u in urls if "window.location" in u or "/link?url=" in u]
    check("搜索链接已还原成真实 URL", not bad, str(bad)[:80])
smoke("fetch_url", {"url": "https://example.com", "max_chars": 60})
text = smoke("search_notes", {"query": "gather 异常"})
if text.startswith("{"):
    check("笔记检索有命中", json.loads(text).get("count", 0) > 0, text[:60])

# ---------------------------------------------------------------- 6. 记忆
print("\n=== 6. 记忆 ===")
smoke("remember", {"key": "_selfcheck", "value": "ok"})
text = smoke("recall", {"query": "_selfcheck"})
check("能读回刚写的事实", "_selfcheck" in text, text[:60])

# ---------------------------------------------------------------- 7. 可选端到端
if "--live" in sys.argv:
    print("\n=== 7. 端到端（会花 token）===")
    from agent import config, loop
    config.load_env()
    cfg = config.settings()
    for q, want in [
        ("上海现在多少度？", "get_weather"),
        ("先查我的笔记里 gather 怎么处理异常，再写进 scratch/结论.md", "search_notes"),
    ]:
        r = loop.run_agent(cfg, q, max_steps=10)
        used = r["tools_used"]
        check(f"端到端命中 {want}", want in used, f"实际={used} 步数={r['steps']}")
        print(f"        答案: {r['answer'][:100]}")

print(f"\n=== 结果：{sum(results)}/{len(results)} 通过 ===")
sys.exit(0 if all(results) else 1)
