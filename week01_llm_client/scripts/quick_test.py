"""临时验证 chat()：成功路径 + 401 不重试 + 网络错误重试。验收完可以删。"""
import asyncio

import httpx

from llm_client import LLMClient, Settings
from llm_client.logger_setup import setup_logger

setup_logger("llm_client")                 # ★ 关键：让 client.py 里的日志可见
log = setup_logger("quick_test")


async def main():
    print("\n===== 场景 1：正常调用 =====")
    async with LLMClient(Settings()) as client:
        text = await client.chat("用一句话说明什么是异步IO", thinking=False)
        print("回答:", text[:60], "...")
        print("累计 tokens:", client.total_tokens)

    print("\n===== 场景 2：4xx 不重试（故意用错 Key）=====")
    bad = Settings()
    bad.api_key = "sk-wrong-key-1234567890"
    try:
        async with LLMClient(bad) as client:
            await client.chat("你好", thinking=False)
    except httpx.HTTPStatusError as e:
        print("捕获到:", e.response.status_code, "→ 应该只有 1 条 ERROR，没有 WARNING")

    print("\n===== 场景 3：网络错误重试（故意用错地址）=====")
    bad2 = Settings()
    bad2.base_url = "https://api.deepseek.invalid"
    try:
        async with LLMClient(bad2) as client:
            await client.chat("你好", thinking=False)
    except Exception as e:
        print("最终失败:", type(e).__name__, e, "→ 应该看到 2 条 WARNING")


if __name__ == "__main__":
    asyncio.run(main())