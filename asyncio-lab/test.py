import asyncio
import sys
import time
import random

async def worker(i):
    try:
        await asyncio.sleep(10)
        return f"任务{i}正常完成"
    except asyncio.CancelledError:
        print(f"任务{i}被取消,执行清理工作")
        raise
async def main():
    tasks = [asyncio.create_task(worker(i), name=f"worker-{i}") for i in range (10)]
    await asyncio.sleep(2)
    print(f"开始取消全部任务")
    for t in tasks:
        t.cancel()

        result = await asyncio.gather(*tasks, return_exceptions=True)
        for t, r in zip(tasks, result):
            state = "已取消" if isinstance(r, asyncio.CancelledError) else r
            print(t.get_name(), "->", state)

if __name__ == "__main__":
    asyncio.run(main())

