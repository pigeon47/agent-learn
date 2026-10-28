r"""带长期记忆的回答主流程。

流程：取相关记忆 → 注入 system prompt → 调 LLM → 抽取新事实 → 写回库。
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from week03_react_agent.agent import llm    # noqa: E402

from .extract import extract_facts          # noqa: E402
from .store import Memory                   # noqa: E402

BASE_SYSTEM = "你是乐于助人的助手，回答简介准确，用中文。"

SUMMARY_PROMPT = """把下面的多轮对话压缩成不超过 150 字的中文摘要。

保留：
1. 用户说过的身份、偏好、目标、限制；
2. 已经做出的决定和结论；
3. 尚未完成的待办。

丢弃：寒暄、重复内容、与后续无关的细节。
只输出摘要正文，不要加任何前缀或解释。
"""


def compress_history(cfg: dict, history: list[dict], keep_last_turns: int = 2) -> list[dict]:
    """把较早的消息压成一条摘要，保留最近 keep_last_turns 轮原文。

    返回新的 history（不修改原列表），
    这样外层可以比较压缩前后的 token 变化。
    """
    keep_msgs = keep_last_turns * 2          # 一轮 = user + assistant
    if len(history) <= keep_msgs:
        return history

    old, tail = history[:-keep_msgs], history[-keep_msgs:]
    transcript = "\n".join(f"{m['role']}: {m['content'][:400]}" for m in old)
    messages = [
        {"role": "system", "content": SUMMARY_PROMPT},
        {"role": "user", "content": transcript},
    ]
    message, _usage = llm.chat(cfg, messages)
    summary = (message.get("content") or "").strip()
    return [{"role": "user", "content": f"（早前对话摘要）{summary}"}] + tail



def ask(cfg: dict, memory: Memory, question: str,
        history: list[dict] | None = None,
        use_memory: bool = True,
        do_extract: bool = True,
        top_k: int = 5) -> dict:
    """返回 {answer, mem_text, new_facts, usage}。
    
    history: 可选的会话的历史 (会被原地追加本轮问答，实现短期记忆)。
    use_memory：关掉可做"无记忆"对照实验。
    do_extract：关掉可省一次调用 (评测时用)
    """

    mem_text = memory.as_prompt(question, limit=top_k) if use_memory else ""

    system = BASE_SYSTEM
    if mem_text:
        system = f"{BASE_SYSTEM}\n\n{mem_text}\n\n请自然地使用这些已知信息，不要生硬复述"

    messages: list[dict] = [{"role": "system", "content": system}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    message, usage = llm.chat(cfg, messages)
    answer = (message.get("content") or "").strip()

    new_fact: list[dict] = []
    if use_memory and do_extract:
        new_fact = extract_facts(cfg, question, answer)
        for f in new_fact:
            memory.upsert(f["key"], f["value"])

    if history is not None:
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})

    return {"answer": answer, "mem_text": mem_text,
            "new_facts": new_fact, "usage": usage}