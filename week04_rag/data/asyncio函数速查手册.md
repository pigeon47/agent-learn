# asyncio 函数速查手册

配套《Python asyncio 实战讲义》使用的速查表。按用途分类，随时对照。

**标记说明**：★ = 已经学过的 ☆ = 还没学过但该知道的

## 一、asyncio 函数总表

### 1. 启动与事件循环

| 函数 | 作用 | 备注 |
|---|---|---|
| ★ `asyncio.run(coro)` | 启动事件循环、运行一个协程、返回结果、关掉循环 | 全程序只调一次，不能嵌套 |
| ☆ `asyncio.get_running_loop()` | 拿到当前正在运行的事件循环对象 | 在协程内部使用 |
| ☆ `asyncio.Runner()` | 3.11+ 上下文管理器，同一循环里多次 run | 一般用不到 |
| ☆ `asyncio.get_event_loop()` | 旧写法 | 已弃用，不要用 |

### 2. 创建与调度任务

| 函数 | 作用 | 备注 |
|---|---|---|
| ★ `asyncio.create_task(coro, name=...)` | 把协程包成 Task 并立刻排入事件循环 | 返回值必须存进变量或列表 |
| ★ `asyncio.TaskGroup()` | 结构化并发：with 退出时自动等全部结束；失败自动取消兄弟 | 3.11+，用 `async with ... as tg:` |
| ☆ `asyncio.ensure_future(obj)` | 把 awaitable 转成 Task | 底层 API，少用 |
| ☆ `asyncio.current_task()` | 拿到当前正在执行的 Task | 调试用 |
| ☆ `asyncio.all_tasks()` | 列出还没结束的所有 Task | 调试用 |

### 3. 等待与收集结果

| 函数 | 作用 | 关键区别 |
|---|---|---|
| ★ `asyncio.gather(*aws, return_exceptions=False)` | 并发跑一批，全部完成后按传入顺序返回结果列表 | 失败默认抛出，兄弟任务不取消 |
| ☆ `asyncio.as_completed(aws, timeout=None)` | 谁先完成先交出谁，边完成边处理 | 顺序 = 完成顺序 |
| ☆ `asyncio.wait(aws, timeout=None, return_when=...)` | 更底层，返回 done 和 pending 两个集合 | 必须传 Task，传协程会报错 |
| ☆ `asyncio.shield(aw)` | 保护某个任务不被外部取消 | 外层被取消时它继续跑 |

### 4. 超时与取消

| 函数或异常 | 作用 |
|---|---|
| ☆ `asyncio.wait_for(aw, timeout)` | 等待协程，超时就取消它并抛 TimeoutError；timeout=None 表示不限 |
| ☆ `asyncio.timeout(delay)` | 3.11+ 上下文管理器版：`async with asyncio.timeout(5):` |
| ☆ `asyncio.sleep(delay, result=None)` | 异步睡眠，不阻塞事件循环 |
| ☆ `Task.cancel()` | 请求取消，不是立刻生效，要等下一个 await 点 |
| ☆ `asyncio.CancelledError` | 取消时抛出，继承 BaseException 而不是 Exception |

注意：正因为 CancelledError 不是 Exception 子类，用 `isinstance(r, Exception)` 判定不出被取消的任务 —— 要判断取消必须写 `isinstance(r, asyncio.CancelledError)`。

### 5. 同步原语（限流 / 锁 / 队列）

| 对象 | 作用 | 常用方法 |
|---|---|---|
| ★ `asyncio.Semaphore(n)` | 限制并发数，同时最多 n 个 | acquire / release / async with |
| ☆ `asyncio.BoundedSemaphore(n)` | 同上，但 release 超次数会报错，防 bug | 同上 |
| ☆ `asyncio.Lock()` | 互斥锁，保护共享资源 | acquire / release / async with |
| ☆ `asyncio.Event()` | 事件标志，一个任务等另一个任务发信号 | wait / set / clear / is_set |
| ☆ `asyncio.Condition()` | 条件变量，生产者-消费者场景 | wait / notify / notify_all |
| ☆ `asyncio.Queue(maxsize=0)` | 协程安全的队列，生产者-消费者最常用 | put / get / join / task_done |
| ☆ `asyncio.LifoQueue` 与 `asyncio.PriorityQueue` | 后进先出队列 / 优先级队列 | 同 Queue |
| ☆ `asyncio.Barrier(n)` | 3.11+ 屏障，等够 n 个再一起走 | wait |

### 6. 与线程 / 进程协作

| 函数 | 作用 |
|---|---|
| ☆ `asyncio.to_thread(func, *args)` | 3.9+ 把阻塞函数丢到线程池执行，避免卡死事件循环 |
| ☆ `loop.run_in_executor(executor, func)` | 同上，但可指定 ProcessPoolExecutor 做 CPU 密集任务 |

## 二、Task 对象的方法

| 方法 | 作用 |
|---|---|
| `task.result()` | 取返回值；没完成会抛 InvalidStateError，失败会重新抛出异常 |
| `task.exception()` | 取异常对象，没异常返回 None，不会抛出 |
| `task.done()` | 是否已结束，正常完成或被取消都算 |
| `task.cancelled()` | 是否被取消 |
| `task.cancel()` | 请求取消，返回 True 或 False |
| `task.get_name()` 与 `set_name()` | 任务名，日志里非常有用 |
| `task.add_done_callback(fn)` | 完成时回调，不推荐在 async 代码里用 |
| `task.cancelling()` 与 `uncancel()` | 3.11+，取消计数 |

## 三、常用异常速查

| 异常 | 什么时候出现 |
|---|---|
| `asyncio.CancelledError` | 任务被取消，是 BaseException 子类 |
| `asyncio.TimeoutError` | 3.11+ 就是内置 TimeoutError，属于 OSError 子类 |
| `asyncio.InvalidStateError` | 对未完成的 Task 调 result() |
| RuntimeError：asyncio.run cannot be called from a running event loop | 嵌套调用 asyncio.run |
| RuntimeError：TaskGroup has not been entered | 在 async with 外面调 tg.create_task() |
| RuntimeWarning：coroutine was never awaited | 创建了协程却没有 await |
| `ExceptionGroup` 配合 `except*` | 3.11+ TaskGroup 失败时抛出的异常组 |

## 四、Python 相关函数

### 1. 随机 random

| 函数 | 返回 |
|---|---|
| `random.random()` | 0.0 到 1.0 之间的浮点数，不含 1.0 |
| `random.uniform(a, b)` | a 到 b 之间的浮点数，两端都含 |
| `random.randint(a, b)` | a 到 b 之间的整数，含两端 |
| `random.randrange(a, b)` | a 到 b 之间的整数，不含右端 |
| `random.choice(seq)` | 序列里随机一个元素 |
| `random.choices(seq, k=n)` | n 个元素，可重复 |
| `random.sample(seq, k=n)` | n 个元素，不重复 |
| `random.shuffle(lst)` | 原地打乱列表 |
| `random.gauss(mu, sigma)` | 正态分布 |
| `random.seed(x)` | 设定随机序列起点，返回 None |
| `random.Random(x)` | 独立的随机数生成器实例 |

### 2. 时间 time

| 函数 | 用途 |
|---|---|
| `time.perf_counter()` | 高精度单调计时器，测耗时就用它 |
| `time.time()` | 墙钟时间戳，会被系统改时间影响 |
| `time.monotonic()` | 单调时钟 |
| `time.sleep(秒)` | 同步阻塞，协程里禁用，会卡死整个事件循环 |

### 3. 内置函数（最常用的一批）

| 函数 | 作用 |
|---|---|
| `print(*args, sep, end, file, flush)` | 打印 |
| `len` / `sum` / `max` / `min` / `abs` | 聚合与取绝对值 |
| `round(x, n)` | 四舍六入五成双，不是四舍五入 |
| `range(start, stop, step)` | 整数序列，不含 stop |
| `enumerate(it, start=0)` | 带下标的遍历 |
| `zip(*its)` | 并行遍历多个序列 |
| `isinstance(x, T)` 与 `type(x)` | 类型判断 |
| `repr(x)` 与 `str(x)` | 原始表示与字符串表示 |
| `int` / `float` / `str` / `list` / `dict` / `set` | 类型转换 |
| `sorted(it, key=, reverse=)` 与 `reversed()` | 排序与反转 |
| `any()` 与 `all()` | 有任一为真 / 全部为真 |
| `input(prompt)` | 读一行输入，返回字符串 |
| `open(file, mode, encoding=)` | 打开文件 |
| `hasattr` / `getattr` / `setattr` | 属性操作 |

### 4. 字符串与格式化

| 写法 | 作用 |
|---|---|
| `strip` / `lstrip` / `rstrip` | 去掉首尾空白 |
| `split(sep)` 与 `sep.join(list)` | 分割与拼接 |
| `replace(a, b)` 与 `lower()` 与 `upper()` | 替换与大小写 |
| `startswith` 与 `endswith` 与 `removesuffix` | 前后缀判断与删除 |
| `f"{x}"` | f-string 插值，漏写 f 就不会替换 |
| `f"{x:.2f}"` | 保留 2 位小数 |
| `f"{i:3d}"` 与 `f"{i:03d}"` | 宽度 3 与补零到 3 位 |
| `f"{i:<5}"` 与 `f"{i:^5}"` | 左对齐与居中 |
| `f"{n:,}"` | 千分位，如 1,234,567 |
| `f"{x:.1%}"` | 百分比，如 25.6% |
| `f"{x!r}"` | 用 repr 显示 |
| `f"{x=}"` | 调试神器，输出 x=值 |

### 5. 解包与作用域

| 写法 | 作用 |
|---|---|
| `a, b = t` | 元组解包，函数返回多个值其实返回元组 |
| `a, *rest = lst` | 带星号解包 |
| `f(*args)` | 调用时摊开参数 |
| `def f(*args, **kwargs)` | 定义时收集参数 |
| `global x` | 声明要改的是模块级变量 |
| `nonlocal x` | 声明要改的是外层函数的变量 |
| `if __name__ == "__main__":` | 只有本文件被直接运行时才执行的入口 |

### 6. 异常与流程

| 写法 | 作用 |
|---|---|
| `try / except / else / finally` | 捕获异常，finally 一定执行，适合释放资源 |
| `except (A, B) as e:` | 一次捕获多种异常 |
| `raise SomeError("消息")` | 主动抛异常 |
| `raise`（裸 raise） | 重新抛出当前异常，只能写在 except 里 |
| `except*` | 3.11+ 捕获异常组，配 TaskGroup 使用 |
| `sys.exit(1)` | 结束程序，1 表示异常退出，0 表示正常 |
| `sys.argv` | 命令行参数列表，第 0 个是文件名 |

## 五、五个可直接套用的模板

### 模板 1：并发调 API（限流 + 重试 + 异常收集）

```python
import asyncio, random

async def call_api(i, sem, retries=3, timeout=5):
    async with sem:                                   # 限流
        for attempt in range(retries):
            try:
                return await asyncio.wait_for(one_call(i), timeout)
            except (asyncio.TimeoutError, RuntimeError):
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(0.5 * 2 ** attempt)   # 指数退避

async def main():
    sem = asyncio.Semaphore(5)
    results = await asyncio.gather(*(call_api(i, sem) for i in range(50)),
                                   return_exceptions=True)
    ok = [r for r in results if not isinstance(r, Exception)]
    print(f"成功 {len(ok)}/{len(results)}")
```

### 模板 2：结构化并发（失败即全停）

```python
async def main():
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(work(1))
        t2 = tg.create_task(work(2))
    print(t1.result(), t2.result())      # 出了 with 块才有结果
```

### 模板 3：流式处理（谁先完成先处理）

```python
async def main():
    tasks = [asyncio.create_task(job(i)) for i in range(10)]
    for coro in asyncio.as_completed(tasks):
        print(await coro)
```

### 模板 4：超时控制

```python
# 写法 A：给单个调用加超时
result = await asyncio.wait_for(slow_task(), timeout=5)

# 写法 B：给一整段代码加超时（3.11+）
async with asyncio.timeout(5):
    await slow_task_a()
    await slow_task_b()
```

### 模板 5：包装阻塞函数

```python
result = await asyncio.to_thread(requests.get, url, timeout=10)
```

## 六、坑速查表

| 坑 | 后果与正确做法 |
|---|---|
| await 写在 for 循环里 | 没有并发，退化成串行，应该用 gather 或 TaskGroup |
| 协程里用 time.sleep 或 requests | 卡死整个事件循环，应该用 asyncio.sleep 或 httpx 或 to_thread |
| create_task 返回值不保存 | 任务可能被垃圾回收、中途消失 |
| gather 不加 return_exceptions=True | 一个失败就抛异常，其他结果全丢 |
| async def 调用后不 await | 什么都不执行，还会报 RuntimeWarning |
| 嵌套调用 asyncio.run() | RuntimeError：不能在运行中的事件循环里再 run |
| Semaphore 在模块顶层创建并跨多次 run | 绑定旧事件循环报错，应该放进 main 里创建 |
| await tg.create_task(...) | 语法合法但会退化成串行 |
| 用 isinstance(e, Exception) 判断取消 | CancelledError 是 BaseException，判定不出来 |
| 提前 break 出 as_completed | 剩余任务不会自动取消，要手动 cancel() |
| 固定随机种子就以为耗时也稳定 | 种子只固定数值序列，墙钟耗时仍会波动 |

## 七、版本要求表

| 特性 | 最低版本 |
|---|---|
| async 与 await | 3.5 |
| asyncio.run() | 3.7 |
| asyncio.to_thread() | 3.9 |
| as_completed 的 timeout 参数 | 3.10 |
| TaskGroup 与 asyncio.timeout 与 except* | 3.11 |
| f-string 里嵌套同类引号 | 3.12 |

当前环境是 Python 3.12.15，上表全部可用。

## 八、按需求反查（我想做什么，该用哪个）

| 我想…… | 用什么 |
|---|---|
| 并发跑一批任务，拿到全部结果 | `asyncio.gather` |
| 谁先完成先处理 | `asyncio.as_completed` |
| 一个失败就全部停掉 | `asyncio.TaskGroup` |
| 限制同时最多几个任务 | `asyncio.Semaphore` |
| 给单个调用加超时 | `asyncio.wait_for` |
| 给一整段代码加超时 | `asyncio.timeout` |
| 手动取消任务 | `Task.cancel` 加 await gather 等它结束 |
| 拿到被取消任务的结局 | `gather(..., return_exceptions=True)` |
| 调用阻塞的老库 | `asyncio.to_thread` |
| 生产者-消费者模式 | `asyncio.Queue` |
| 多个任务等一个信号 | `asyncio.Event` |
| 保护任务不被取消 | `asyncio.shield` |
| 看某个任务的进度与状态 | `Task.done` 与 `Task.result` 与 `Task.get_name` |

## 九、一句话总结

- 并发结构：`gather`（全等，顺序固定）、`as_completed`（谁快谁先）、`TaskGroup`（结构化，失败全停）
- 限流保护：`Semaphore`（限并发）、`Queue`（限速与缓冲）、`Lock`（保共享资源）
- 超时取消：`wait_for`（单次）、`timeout`（代码块）、`Task.cancel`（手动）
- 别踩的坑：协程里别用阻塞调用、`create_task` 的引用要存、`CancelledError` 不是 Exception
