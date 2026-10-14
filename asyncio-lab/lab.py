"""
asyncio 练习骨架 —— 对应《Python asyncio 实战讲义》第三节的 6 个版本。

用法：
    python lab.py v0     # 同步，约 5 秒
    python lab.py v1     # async 但 await 写在循环里，仍然约 5 秒
    python lab.py v2     # gather 并发，约 1 秒
    python lab.py v3     # 加 Semaphore 限流
    python lab.py v4     # 超时 + 重试 + return_exceptions
    python lab.py v5     # TaskGroup（需要 Python 3.11+）

现在每个函数体都是空的，把讲义里的代码自己敲进来。不要复制粘贴。
每跑完一个版本，把耗时记到 notes.md 里。
"""

import asyncio
import sys
import time
import random


# ---------------------------------------------------------------------------
# 版本 0：同步写法，5 个任务各等 1 秒，总耗时约 5 秒
# ---------------------------------------------------------------------------
def v0_sync():
    def fetch(i):
        time.sleep(1)
        return i * 2
    
    if __name__ == "__main__":
        start = time.perf_counter()
        print([fetch(i) for i in range(5)])
        print("耗时", round(time.perf_counter() - start, 2),"秒")   #约5.0秒


# ---------------------------------------------------------------------------
# 版本 1：改成 async，但 await 写在 for 循环里 —— 陷阱！仍然约 5 秒
# ---------------------------------------------------------------------------
async def v1_serial():
    async def fetch(i):
        await asyncio.sleep(1)
        return i * 2

    results = []
    for i in range(5):
        results.append(await fetch(i))
    return results


# ---------------------------------------------------------------------------
# 版本 2：用 asyncio.gather 真正并发，耗时约 1 秒
# 另：再写一个 as_completed 版本，谁先返回谁先处理
# ---------------------------------------------------------------------------
async def v2_gather():
    async def fetch(i):
        await asyncio.sleep(1)
        return i * 2
    return await asyncio.gather(*(fetch(i) for i in range (5)))

# ---------------------------------------------------------------------------
# 版本 3：加 Semaphore 限流，最多同时 3 个
# ---------------------------------------------------------------------------
async def v3_limited():
    async def fetch(i, sem):
        async with sem:
            await asyncio.sleep(1)
            return i * 2
    sem = asyncio.Semaphore(10)
    return await asyncio.gather(*(fetch(i, sem) for i in range(100)))


# ---------------------------------------------------------------------------
# 版本 4：超时 + 重试 + 异常收集（最接近生产可用）
# ---------------------------------------------------------------------------
async def v4_robust():
    async def one_call(i):
        await asyncio.sleep(random.uniform(0.2, 1.0))
        if random.random() < 0.3:
            raise RuntimeError("模拟网络错误")
        return f"任务{i}成功"
    async def call_api(i, timeout=5, retries=3):
        for attempt in range(retries):
            try:
                return await asyncio.wait_for(one_call(i), timeout)
            except (asyncio.TimeoutError, RuntimeError):
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(0.5 * 2 ** attempt)
    sem = asyncio.Semaphore(5)
    async def guarded(i):
        async with sem:
            return await call_api(i)
    results = await asyncio.gather(*(guarded(i) for i in range(20)), return_exceptions = True)  #关键参数return_exceptions = True，如果没有的话异常会上抛，其他任务不取消，在后台继续跑，会程序错误但是依然运行
    ok = [r for r in results if not isinstance(r, Exception)]
    bad = [r for r in results if isinstance(r, Exception)]
    print (f"成功{len(ok)}个，失败{len(bad)}个")
    for b in bad:
        print ("失败原因：", repr(b))


# ---------------------------------------------------------------------------
# 版本 5：TaskGroup（Python 3.11+）
# 体会：一个任务失败时，兄弟任务会被自动取消（gather 不会）
# ---------------------------------------------------------------------------
async def v5_taskgroup():
    async def fetch(i):
        await asyncio.sleep(0.5)
        return i
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(fetch(1))
        t2 = tg.create_task(fetch(2))
    print(t1.result(), t2.result())


# ---------------------------------------------------------------------------
# 入口：用命令行参数选择要运行的版本
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        version = sys.argv[1]                              # 命令行有参数就用参数
    else:
        version = input("要运行哪个版本？（v0~v5，直接回车=v0）: ").strip() or "v0"

    print(f">>> 正在运行 {version}")

    start = time.perf_counter()

    if version == "v0":
        v0_sync()
    elif version == "v1":
        print(asyncio.run(v1_serial()))
    elif version == "v2":
        print(asyncio.run(v2_gather()))
    elif version == "v3":
        print(asyncio.run(v3_limited()))
    elif version == "v4":
        asyncio.run(v4_robust())
    elif version == "v5":
        asyncio.run(v5_taskgroup())
    else:
        print(f"未知版本：{version}（可选 v0 v1 v2 v3 v4 v5）")
        sys.exit(1)

    print(f"总耗时 {time.perf_counter() - start:.2f} 秒")
