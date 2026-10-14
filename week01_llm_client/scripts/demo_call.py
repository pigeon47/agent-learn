r"""环境冒烟测试：不经任何封装，直接用 httpx 调一次 DeepSeek。

这个脚本是【已写好、可直接运行】的，作用是先确认三件事都正常：
  1. .env 读到了，Key 有效
  2. 网络通，base_url 正确
  3. 能拿到 usage（后面做 token 统计要用）

跑通它，再动手实现 llm_client/client.py 里的 chat()。

运行（必须在项目根目录）：
    ..\env\python.exe -m scripts.demo_call

小知识：这个文件的文档字符串前面加了一个字母 r，表示 raw string。
因为里面有 Windows 路径 ..\env\...，其中反斜杠 e 在普通字符串里是无效转义序列，
会触发 SyntaxWarning，加上 r 前缀就没事了。
"""

import asyncio

import httpx

from llm_client.config import Settings
from llm_client.logger_setup import setup_logger

log = setup_logger("demo_call")


async def main():
    s = Settings()
    log.info("配置就绪 -> %s", s)          # 注意：api_key 会被脱敏显示

    async with httpx.AsyncClient(base_url=s.base_url) as client:
        r = await client.post(
            "/chat/completions",
            headers={"Authorization": f"Bearer {s.api_key}"},
            json={
                "model": s.model,
                "messages": [{"role": "user", "content": "用一句话说明什么是异步IO"}],
                "thinking": {"type": "disabled"},      # 冒烟测试关掉思考，快很多
            },
            timeout=httpx.Timeout(connect=10.0, read=s.timeout, write=30.0, pool=10.0),
        )
        r.raise_for_status()
        data = r.json()

    u = data["usage"]
    choice = data["choices"][0]

    print()
    print("=" * 60)
    print("模型回答：", choice["message"]["content"])
    print("=" * 60)
    print(f"model          : {data['model']}")
    print(f"finish_reason  : {choice['finish_reason']}")
    print(f"total_tokens   : {u['total_tokens']}")
    print(f"  prompt       : {u['prompt_tokens']}")
    print(f"  completion   : {u['completion_tokens']}")
    thinking_tokens = u.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
    print(f"  reasoning    : {thinking_tokens}   （关掉 thinking 后应为 0）")
    print()

    log.info("冒烟测试通过")


if __name__ == "__main__":
    asyncio.run(main())
