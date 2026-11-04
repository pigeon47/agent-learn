"""代码的执行：子进程 + 超时 + 输出截断。"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time

from .base import SCRATCH

# 只匹配 sk- 开头、后接 20 位以上字母数字/下划线/短横（DeepSeek Key 形态）
_SECRET_RE = re.compile(r"sk-[A-Za-z0-9_\-]{20,}")
def _redact(text: str) -> tuple[str, bool]:
    """把输出里的真 Key 打码。只认真 Key 与 sk- 形态，不碰普通大数。"""
    hit = False
    for name in ("DEEPSEEK_API_KEY",):
        real = os.environ.get(name)
        if real and len(real) >= 8 and real in text:
            text = text.replace(real, "sk-***REDACTED***")
            hit = True
    text, n = _SECRET_RE.subn("sk-***REDACTED***", text)
    return text, hit or n > 0



def python_exec(code: str, timeout: int = 15) -> dict:
    if len(code) > 8000:
        raise ValueError(f"代码太长 (上限 8000 字符) ")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    script = SCRATCH / f"run_{int(time.time() * 1000)}.py"
    script.write_text(code, encoding="utf-8")
    env = {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "TEMP": os.environ.get("TEMP", ""),
    }
    t0 = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, cwd=str(SCRATCH), env=env,
        )
        out, hit_out = _redact(proc.stdout or "")
        err, hit_err = _redact(proc.stderr or "")
        return {"ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": out[:3000],
                "stderr": err[-1500:],
                "redacted": hit_out or hit_err,
                "duration_s": round(time.time() - t0, 2)}
    except subprocess.TimeoutExpired:
        return {"ok": False, "exit_code": -1, "stdout": "",
                "stderr": f"执行超时 (>{timeout} 秒)", "duration_s": timeout}


SPECS= [
    {
        "type": "function",
        "function": {
            "name": "python_exec",
            "description": (
                "执行一段 Python 代码并返回输出，需要精确计算、统计、数据处理、"
                "字符串/日期处理，验证想法时调用，不要心算。代码里用 print 输出结果。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "完整 Python 代码"},
                    "timeout": {"type": "integer", "descriptiom": "超时秒数，默认 15"},
                },
                "required": ["code"],
            },
        },
    },
]

IMPL = {"python_exec": python_exec}
