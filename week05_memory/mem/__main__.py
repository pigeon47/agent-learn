r"""第 5 周 CLI。

用法：
    python -m mem --chat                    多轮对话（带记忆）
    python -m mem --chat --session alice    指定会话（记忆隔离）
    python -m mem --memory                  查看当前会话记住的事实
    python -m mem --reset                   清空当前会话记忆
    python -m mem --eval                    跑 10 题 A/B 对比
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from week03_react_agent.agent import config as llm_config   # noqa: E402

from .chat import ask, compress_history                     # noqa: E402
from .store import Memory                                   # noqa: E402



def show_results(r: str) -> None:
    print(f"助手> {r['answer']}")
    if r["new_facts"]:
        print("     (新记住： " + "、".join(f"{f['key']}={f['value'][:12]}" for f in r["new_facts"]) + ")")
        if r["mem_text"]:
            used = r["mem_text"].splitlines()[1:]
            print(f"    (用到 {len(used)} 条记忆)")



def main() -> None:
    parser = argparse.ArgumentParser(description="第 5 周：记忆与状态管理")
    parser.add_argument("--session", default="default", help="会话名，用于记忆隔离")
    parser.add_argument("--chat", action="store_true", help="进入多轮对话")
    parser.add_argument("--memory", action="store_true", help="列出已记住的事实")
    parser.add_argument("--reset", action="store_true", help="清空当前会话记忆")
    parser.add_argument("--no-memory", action="store_true", help="关闭长期记忆（对照组）")
    parser.add_argument("--eval", action="store_true", help="跑 A/B 评测")
    parser.add_argument("--no-compress", action="store_true", help="关闭短期记忆压缩")
    parser.add_argument("--max-turns", type=int, default=4, help="超过几轮后压缩早期对话")
    args = parser.parse_args()

    llm_config.load_env()
    cfg = llm_config.settings()

    if args.eval:
        from .evaluate import main as eval_main
        eval_main()
        return

    memory = Memory(session=args.session)

    if args.reset:
        n = memory.forget()
        print(f"已清空会话 {args.session} 的 {n} 条记忆")
        return

    if args.memory:
        rows = memory.all()
        print(f"会话 {args.session} 共 {len(rows)} 条记忆：")
        for r in rows:
            print(f"  {r['key']:18s} = {r['value']}")
        return

    if not args.chat:
        parser.print_help()
        return

    history: list[dict] = []
    print(f"多轮对话（会话={args.session}，记忆={'开' if not args.no_memory else '关'}），输入 exit 退出。")
    while True:
        try:
            q = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if q.lower() in {"exit", "quit", "q"}:
            break
        if not q:
            continue
        r = ask(cfg, memory, q, history=history, use_memory=not args.no_memory)
        show_results(r)
        u = r["usage"]
        print(f"      （token: {u.get('prompt_tokens', 0)} + {u.get('completion_tokens', 0)}"
              f"，历史 {len(history)} 条）")
        if not args.no_compress and len(history) >= args.max_turns * 2:
            before = u.get("prompt_tokens", 0)
            history = compress_history(cfg, history)
            print(f"      （已压缩历史：{len(history)} 条，上一轮 prompt {before} token）")
    memory.close()

if __name__ == "__main__":
    main()