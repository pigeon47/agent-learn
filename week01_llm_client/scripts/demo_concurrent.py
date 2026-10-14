r"""必做 2：并发调用 + 参数对比实验。

运行（必须在项目根目录）：
    ..\env\python.exe -m scripts.demo_concurrent

产出：
  - 控制台打印对比结果
  - 项目根目录生成 temperature_compare.md（这是你第 1 周的实验证据）

两个实验的知识点：
  A. temperature：控制随机性。0 几乎每次一样，2.0 天马行空。
     必须先关掉思考模式（thinking disabled），否则该参数无效，5 次结果会一模一样。
  B. reasoning_effort：控制思考深度（none / low / high / max）。
     开着思考模式才有意义，效果体现在耗时和 reasoning_tokens 上。

（文档字符串前面加了字母 r，因为里面有 Windows 路径 ..\env\...。）
"""

import asyncio

from llm_client import LLMClient, Settings
from llm_client.logger_setup import setup_logger

setup_logger("llm_client")
log = setup_logger("demo_concurrent")

log = setup_logger("demo_concurrent")

QUESTION = "用一句话说明什么是向量数据库"
TEMPERATURES = [0.0, 0.7, 1.0, 1.5, 2.0]
EFFORTS = ["none", "low", "high", "max"]


async def compare_temperature(client: LLMClient):
    """实验 A：同一个问题、不同 temperature，各调 2 次，看输出稳不稳定。

    实现提示：
      1. 对 TEMPERATURES 里的每个值，调 2 次：
             await client.chat(QUESTION, temperature=t, thinking=False)
         （thinking=False 是关键，否则 temperature 无效）
      2. 记录这 2 次的回答是否相同（相同记为"稳定"）
      3. 用 asyncio.gather 把不同 temperature 的调用并发跑起来，
         外层用 asyncio.Semaphore(5) 限流（复用你练习 3 的结构）
      4. 打印成表格：temperature | 回答1前30字 | 回答2前30字 | 是否一致
      5. 把这个表格也写进 temperature_compare.md
    """
    raise NotImplementedError("实现实验 A：temperature 对比")


async def compare_effort(client: LLMClient):
    """实验 B：不同 reasoning_effort，看耗时和思考 token。

    实现提示：
      1. 对 EFFORTS 里的每个值调一次：
             await client.chat(QUESTION, thinking=True, reasoning_effort=e)
         （注意 reasoning_effort="none" 等于关闭思考）
      2. 用 time.perf_counter() 记录每次耗时
      3. 思考 token 要从响应里拿 —— 现在 chat() 只返回文本，
         你可以先打印 client.total_tokens 的差值来近似，
         或者把 chat() 改成返回 (文本, usage) 元组（推荐，更精确）
      4. 打印表格：effort | 耗时 | 回答前30字
    """
    raise NotImplementedError("实现实验 B：reasoning_effort 对比")


async def main():
    settings = Settings()

    async with LLMClient(settings) as client:
        await compare_temperature(client)
        await compare_effort(client)

        print()
        print(f"本次共消耗 {client.total_tokens} tokens")


if __name__ == "__main__":
    asyncio.run(main())
