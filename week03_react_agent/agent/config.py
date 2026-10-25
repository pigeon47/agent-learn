from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

#本文件在agent/ 子目录，比tools_probe.py 深一层，所以要.parent.parent才能到E:\agent-learn
AGENT_DIR = Path(__file__).resolve().parent #...\week03_react_agent\agent
PROJECT_DIR = AGENT_DIR.parent              #...\week03_react_agent

def load_env() -> None:
    """先找项目.env,再返回week01那份;都没有找到就依赖系统环境。"""
    candidates = [
        PROJECT_DIR / ".env",
        PROJECT_DIR.parent / "week01_llm_client" / ".env",
    ]
    for path in candidates:
        if path.exists():
            load_dotenv(path)
            print(f"[配置]读取{path}")
        load_dotenv()
def settings() -> dict:
    """返回{"api_key","base_url","model","timeout"};缺Key立即退出"""
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        sys.exit(
            "缺少 DEEPSEEK_API_KEY。\n"
            " 修法:把week01_llm_cilent/.env 复制到 week03_react_agnet/.env,"
            "或设置系统环境变量"
        )
    return {
        "api_key" : key,
        "base_url": os.environ.get("DEEPSEEK_BASE_URL","https://api.deepseek.com").rstrip("/"),
        "model": os.environ.get("DEEPSEEK_MODEL","deepseek-flash"),
        "timeout": float(os.environ.get("DEEPSEEK_TIMEOUT","90")),
    }