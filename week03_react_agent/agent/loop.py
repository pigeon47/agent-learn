"""ReAct 循环：想 → 做 → 看，最多 max_steps 步。"""
from __future__ import annotations

import json

from . import llm, tools



def run_agent(cfg: dict, question: str, max_steps: int = 6) -> dict:
    """跑一次完整任务,返回结果字典 (含轨迹,便于复盘)。"""
    messages: list[dict] = [{"role": "user","content": question}]
    trace: list[dict] = []
    tools_used: list[str] = []
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0}

    for step in range(1, max_steps + 1):
        message, usage = llm.chat(cfg, messages, tools.TOOLS)
        usage_total["prompt_tokens"] += usage.get("prompt_tokens", 0)
        usage_total["completion_tokens"] += usage.get("completion_tokens", 0)

        tool_calls = message.get("tool_calls")

        # 没有 tool_call = 模型给出最终答案,循环结束
        if not tool_calls:
            answer = (message.get("content") or "").strip()
            trace.append({"step": step, "type": "answer", "content": answer})
            return {
                "answer": answer or "(模型返回了空内容)",
                "steps": step,
                "tools_used": tools_used,
                "usage": usage_total,
                "trace": trace,
                "stopped": "answered",
            }

        # ★ 关键：assistant 消息必须原样放回历史，否则模型不知道自己要过工具
        messages.append(message)

        for tc in tool_calls:
            name = tc["function"]["name"]
            raw_args = tc["function"]["arguments"] or "{}"
            try:
                args = json.loads(raw_args)     # arguments 是字符串, 要 decode
            except json.JSONDecodeError:
                args = {}

            ok, result_text = tools.call_tool(name, args)
            tools_used.append(name)
            trace.append({
                "step": step,
                "type": "tool_call",
                "tool": name,
                "arguments": args,
                "ok": ok,
                "result": result_text,
            })

            # 结果回传: role 固定 "tool", tool_call_id 必须和上面配对
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result_text,
            })

    # 走满 max_steps 还没收尾 → 求助人类（安全策略）
    trace.append({"step": max_steps, "type": "give_up", "content": "达到最大步数"})
    return {
        "answer": f"达到最大步数({max_steps}) 仍未完成,已停止并请求人工介入。",
        "steps": max_steps,
        "tools_used": tools_used,
        "usage": usage_total,
        "trace": trace,
        "stopped": "max_steps",
    }