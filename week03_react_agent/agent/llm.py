"""一次API请求,只负责"发出去,拿回来",不含任何循环逻辑。"""
from __future__ import annotations

import httpx
import json

def chat(cfg: dict, messages: list[dict], tools: list[dict] | None = None) -> tuple[dict, dict]:
    """返回(massages, usage)。

    message 可能长这样 (模型要你执行工具) :
        {"role":"assistant","content":"",tool_calls:[{"id":"call_0_x","type":"function",
        "function":{"name":"get_time","arguments":"{}"}}]}
    也可能长这样 (模型给出最终答案) :
        {"role":"assistant","content":"现在是 2026-10-22 20:15:03。"}
    """

    payload: dict ={
        "model": cfg["model"],
        "messages": messages,
        "temperature": 0.0,
        #思考模式下 tool_choice 会受限、还要回传 reasoning_content，实验期一律关掉
        "thinking": {"type": "disabled"},
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"     #只能用 auto, required/指定工具会 400
    with httpx.Client(timeout=cfg["timeout"]) as client:
        resp = client.post(
            f"{cfg['base_url']}/chat/completions",
            headers = {
                "Authorization": f"Bearer {cfg['api_key']}",
                "Content-Type": "application/json",
            },
            json = payload,
        )

    if resp.status_code != 200:
        raise RuntimeError(f"HTTP{resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    return data["choices"][0]["message"],(data.get("usage") or {})

def chat_stream(cfg: dict, messages: list[dict], tools: list[dict] | None = None,
                on_delta=None) -> tuple[dict, dict]:
    """流式版本: 边收边回调 on_delta(文本片段), 最后返回和 chat() 同形状的 (message, usage).
    
    关注点：
        1.工具调用的轮次里 delta.content 是空的, 只有 tool_calls 分片,
          所以 on_delta 不回打印任何东西-这正是我们要的 (用户看不到内部调度)。
        2.tool_calls 的 arguements 是**分片**拼起来的, 必须按 index 累积。
        3. usage 大多数情况下只在最后一块出现, 取不到就是 0。
    """
    payload: dict = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": 0.0,
        "thinking": {"type": "disabled"},
        "stream": True,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    content_parts: list[str] = []
    tool_slots: dict[int, dict] = {}
    usage: dict = {}

    with httpx.Client(timeout=cfg["timeout"]) as client:
        with client.stream(
            "POST",
            f"{cfg['base_url']}/chat/completions",
            headers={
                "Authorization":f"Bearer {cfg['api_key']}",
                "Content-Type": "application/json",
            },
            json=payload,
        )as resp:
            if resp.status_code != 200:
                body =resp.read().decode("utf-8", "replace")
                raise RuntimeError(f"HTTP {resp.status_code}: {body[:300]}")

            for line in resp.iter_lines():
                line = line.strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[len("data:"):].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                if chunk.get("usage"):
                    usage = chunk["usage"]

                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}

                piece = delta.get("content")
                if piece:
                    content_parts.append(piece)
                    if on_delta:
                        on_delta(piece)

                for tc in delta.get("tool_calls") or []:
                    idx = tc.get("index", 0)
                    slot = tool_slots.setdefault(
                        idx, {"id": "", "type": "function",
                              "function": {"name": "", "arguments": ""}})

                    if tc.get("id"):
                        slot["id"] = tc["id"]
                    fn = tc.get("function") or {}
                    if fn.get("name"):
                        slot["function"]["name"] = fn["name"]
                    if fn.get("arguments"):
                        slot["function"]["arguments"] += fn["arguments"]

        message: dict = {"role": "assistant", "content": "".join(content_parts)}
        if tool_slots:
            message["tool_calls"] = [tool_slots[i] for i in sorted(tool_slots)]
        return message, usage