r"""从一轮回答中抽取 ⌈值得长期记住的用户信息⌋。

只抽事实与偏好，不抽临时问题; key 用小写英文，便于去重与更新
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from week03_react_agent.agent import llm    # noqa: E402

EXTRACT_PROMPT = """你是信息抽取器。从下面的对话中抽取**值得长期记住的用户信息**。

只输出 JSON 格式：{"facts":[{"key": "...", "value": "..."}]}

规则：
1. key 用小写英文和下划线，2~32 字符，例如 name / learning_goal / response_style。
2. 只记用户明确说过的、长期有效的信息（身份、偏好、目标、习惯、限制）。
3. 临时性问题（今天天气、这一次的计算）不要记。
4. 没有可记的信息就输出 {"facts": []}。
5. 不要编造用户没说过的内容。
"""

_KEY_RE = re.compile(r"^[a-z0-9_]{2,32}$")



def _strip_fence(text: str) -> str:
    """去掉模型可能加的 ```json包裹。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()



def extract_facts(cfg: dict, user_text: str, assistant_text: str = "") -> list[dict]:
    """返回 [{"key": ..., "value": ...}]；失败时返回空列表，不抛异常。"""
    payload = f"用户说：{user_text}\n\n助手答：{assistant_text[:200]}"
    messages = [
        {"role": "system", "content": EXTRACT_PROMPT},
        {"role": "user", "content": payload},
    ]
    try:
        message, _usage = llm.chat(cfg, messages)
        data = json.loads(_strip_fence(message.get("content") or ""))
    except Exception:                  # noqa: BLE001 抽取失败不该影响主流程
        return []

    facts: list[dict] = []
    for item in data.get("facts", []) or []:
        key = str(item.get("key", "")).strip().lower()
        value = str(item.get("value", "")).strip()
        if _KEY_RE.match(key) and value:
            facts.append({"key": key, "value": value[:200]})
    return facts



if __name__ == "__main__":
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).resolve().parent.parent.parent))
    from week03_react_agent.agent import config as llm_config

    llm_config.load_env()
    cfg = llm_config.settings()

    samples = [
        "我叫张伟，正在学 AI Agent，目标 12 周内做出可部署的系统",
        "我不喜欢回答里出现表情符号，简洁一点就好",
        "今天天气怎么样？",
    ]
    for s in samples:
        print(f"输入：{s}")
        print(" 抽出：",extract_facts(cfg, s))
        print()
