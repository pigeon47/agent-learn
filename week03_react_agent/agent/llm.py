"""一次API请求,只负责"发出去,拿回来",不含任何循环逻辑。"""
from __future__ import annotations

import httpx

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