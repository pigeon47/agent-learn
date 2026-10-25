# 第 3 周 · 手写 ReAct Agent（不用任何框架）

一个约 190 行的命令行 Agent：把一个问题拆成「想 → 做 → 看」的循环，自己决定调用哪个工具、读工具结果、再给出自然语言答案。

- 模型：`deepseek-flash`，`temperature=0`，思考模式关闭
- 三个工具：当前时间 / 安全计算器 / 天气查询（mock 数据）
- 评测：20 道题，**工具选择准确率 100%（20/20）**，平均每题 **1.9 步**、**963 prompt tokens**
- 安全：最多 6 步，超限主动停止并请求人工介入

---

## 1. 快速开始

```powershell
cd E:\agent-learn\week03_react_agent

# 单问一题（打印完整轨迹）
E:\agent-learn\env\python.exe -m agent "3 的 7 次方乘以 2 是多少？"

# 跑测试集，出准确率与明细
E:\agent-learn\env\python.exe -m agent --eval

# 限制最大步数（观察安全阀）
E:\agent-learn\env\python.exe -m agent --max-steps 1 "帮我查一下杭州的天气。"

# 看参数说明
E:\agent-learn\env\python.exe -m agent --help
```

- 运行环境：`E:\agent-learn\env\python.exe`（Python 3.12）。**不要用 PATH 里的 `python`**（微软商店占位程序，无输出）。
- 依赖：`httpx`、`python-dotenv`。
- Key 复用 `week01_llm_client/.env`（`agent/config.py` 的 `load_env()` 会自动往上找）。
- **必须用 `-m agent` 运行**，不能 `python agent/__main__.py`——包内有相对导入（`from . import llm, tools`），脱离包上下文会报 `attempted relative import with no known parent package`。

产物：

```
results/eval.csv                评测明细（每题一行）
results/eval_schema_broken.csv  参数定义修复前的对照结果
results/trace.jsonl             单题运行的完整轨迹（追加写）
```

---

## 2. 目录结构

```
week03_react_agent/
├── agent/
│   ├── __init__.py      包的标记（一行 docstring，不放任何导入）
│   ├── config.py        load_env() / settings()：读 .env，返回配置 dict
│   ├── llm.py           chat()：一次 API 请求，返回 (message, usage)
│   ├── tools.py         TOOLS（给模型看的 schema）+ TOOL_IMPL（可执行函数）+ call_tool()
│   ├── loop.py          run_agent()：ReAct 主循环 ★核心
│   └── __main__.py      CLI：单问 / --eval / --max-steps
├── data/
│   └── eval_questions.jsonl   20 条测试题（含期望工具）
├── results/
└── README.md
```

依赖方向（避免循环导入）：

```
__main__.py → loop.py → llm.py
                  ↓
               tools.py
config.py ←──（被 llm.py 与 __main__.py 使用）
```

---

## 3. 工作原理

```
messages = [{"role":"user","content":问题}]
     │
     ├─→ llm.chat(messages, tools=TOOLS)
     │        │
     │        ├─ 有 tool_calls → 执行工具 → append(assistant) + append(tool 结果) → 回到上一步
     │        └─ 无 tool_calls → 这就是最终答案 → 结束
     │
     └─→ 达到 max_steps 仍无答案 → 停止并请求人工介入
```

三处容易写错、但决定成败的细节：

**① assistant 消息必须原样放回历史**

```python
messages.append(message)          # message 里带着 tool_calls
```

不放回去，模型就不知道自己上一轮要过工具，第二轮必然对不上。

**② tool 消息必须用 `tool_call_id` 配对**

```python
messages.append({
    "role": "tool",                        # 固定写 "tool"
    "tool_call_id": tc["id"],              # 必须和 assistant 的 tool_call id 一致
    "content": result_text,
})
```

**③ 请求里要显式关掉思考模式**

```python
"thinking": {"type": "disabled"}
```

思考模式下 `tool_choice` 受限（`required` / 指定工具会 400），且多轮工具调用还要回传 `reasoning_content`，实验期一律关闭。

---

## 4. 工具

| 工具 | 参数 | 实现 | 说明 |
|---|---|---|---|
| `get_time` | 无 | `datetime.now()` | 返回当前本地日期时间 |
| `calculator` | `expression: string` | AST 白名单求值 | 只允许数字与 `+ - * / // % **` 和括号，拒绝函数调用/属性访问；指数 > 1000 直接拒绝，防止 `2**999999` 卡死 |
| `get_weather` | `city: string` | 内置 5 城市 mock | 北京 / 上海 / 广州 / 深圳 / 成都 |

**`TOOLS` 和 `TOOL_IMPL` 的分工**：

- `TOOLS`：给**模型**看的 JSON Schema（名字、描述、参数类型），会随请求发出去
- `TOOL_IMPL`：给**代码**用的「名字 → 函数对象」查表，不能序列化，也不发给模型

两者靠 `name` 字符串对齐，用一条断言防止写歪：

```python
assert {t["function"]["name"] for t in TOOLS} == set(TOOL_IMPL)
```

**错误信息的设计**（决定 Agent 能否自我纠正）：

```python
raise ValueError(f"没有 {city} 的天气数据。可用城市：{'、'.join(_WEATHER)}")
```

不只说"查不到"，还把**可用范围**告诉模型，它下一步就能换城市或直接告知用户，而不是盲目重试。

---

## 5. 评测

**方法**：`data/eval_questions.jsonl` 共 20 题，每题标注 `expect_tool`；跑一次 Agent，取 `tools_used[0]` 与 `expect_tool` 比较，相等即算选中。

**结果（`results/eval.csv`）**：

| 指标 | 数值 |
|---|---|
| 题数 | 20 |
| 工具选择正确 | **20 / 20（100%）** |
| 模型调用总次数 | 38（平均 1.9 步/题） |
| 步数分布 | 18 题 2 步，2 题 1 步 |
| 工具分布 | calculator 8、get_time 5、get_weather 5、无需工具 2 |
| prompt tokens 合计 | 19,254（平均 963/题） |
| completion tokens 合计 | 1,487（平均 74/题） |
| **单次调用平均 prompt** | **约 507 tokens** |

**成本观察**：

- 单次请求的 prompt 约 507 token，其中**约 300–400 是三个工具的 schema 定义**。每多挂一个工具，每次调用的固定成本都会上升。
- 需要工具的题走 2 次调用（~1000 prompt），不需要工具的题只走 1 次（~475）。
- 单题 completion 波动很大：`q20`（"什么是提示词工程"）用了 **452 token**，其余题 41–102。**自由问答比工具调用更容易推高成本**。

**评测口径的局限（诚实声明）**：

1. 只测「选没选对工具」，**不测答案是否正确**（答案质量留给第 6 周的 LLM-as-a-Judge）。
2. 只取 `tools_used[0]`，多工具场景可能误判（先调 A 再调 B 时，实际做对但可能被判错）。
3. 20 条样本量小，100% 不代表真实泛化能力。

---

## 6. 失败与自我纠正

`q18`（"帮我查一下杭州的天气"）是故意留的错误样本：mock 里没有杭州，`get_weather` 会抛异常。

实际轨迹（`results/trace.jsonl`）：

```json
{"question": "帮我查一下杭州的天气。", "steps": 2, "stopped": "answered",
 "tools_used": ["get_weather"],
 "trace": [
   {"step": 1, "type": "tool_call", "tool": "get_weather", "ok": false,
    "result": "ValueError: 没有 杭州 的天气数据。可用城市：北京、上海、广州、深圳、成都"},
   {"step": 2, "type": "answer",
    "content": "抱歉，我查不到杭州的天气数据，目前只支持北京、上海、广州、深圳、成都这几个城市……"}
 ]}
```

**2 步完成**：第 1 步工具报错 → 错误信息写回 `messages` → 第 2 步模型读到错误并给出合理回复。这正是「错误信息要能指导纠正」的价值——**好的错误信息省步数、省 token**。

---

## 7. 安全策略

| 策略 | 实现 | 验证方式 |
|---|---|---|
| 最大步数上限 | `run_agent(..., max_steps=6)` | `--max-steps 1` 跑需要工具的题 → `stopped=max_steps`，**不崩溃、不死循环** |
| 卡住时求助人类 | 循环耗尽后返回 `answer="达到最大步数…已停止并请求人工介入"` | 同上，观察返回值 |
| 工具执行失败不抛给主流程 | `call_tool()` 内部 `try/except`，把异常转成字符串回传 | 杭州案例 |
| 计算器防滥用 | AST 白名单 + 指数上限 | `calculator("__import__('os')")` 会被拒绝 |

`max_steps` 的含义是**「允许调用模型几次」**，不是「工具调用次数」：不需要工具的题 1 步够用，需要 1 次工具的题至少 2 步。默认 6 步，实测 20 题最多用 2 步，从未触发上限。

---

## 8. 参数定义实验（修复前后对照）

工具的 `parameters` 里 `properties` 拼错时，模型看到的是空参数表（只剩 `required`）。修复前后各跑一次 20 题：

| 版本 | 工具选择准确率 |
|---|---|
| `properties` 拼错（`promperties` / `promerties`） | 20/20 = 100% |
| 修复后 | 20/20 = 100% |

**结论**：本批题目太简单，模型靠工具名 + `required` 就能猜对参数名，参数描述未产生可测差异。

要验证描述的真实作用，需要加"容易传错参数"的样本，例如：

```json
{"id": "q21", "question": "帮我把「3 的 7 次方乘以 2」这个算式算出来。", "expect_tool": "calculator"}
{"id": "q22", "question": "100 美元按 7.2 的汇率换成人民币是多少？", "expect_tool": "calculator"}
```

这类题模型容易把自然语言整句塞进 `expression`，而描述里那句「不要带单位或文字」正是防这个的。已列入下一步。

---

## 9. 踩过的坑

这一周的 bug 几乎全是「少一个 s 或错一个字母」，而且 **Python 和 JSON 都不会报错**，只有远端服务或后续逻辑会失败：

| 错误写法 | 正确写法 | 表现 |
|---|---|---|
| `"message": messages` | `"messages": messages` | HTTP 400（请求体字段名不符） |
| `data["choice"][0]` | `data["choices"][0]` | `KeyError: 'choice'` |
| `TOOL = [...]` | `TOOLS = [...]` | `AttributeError: module 'agent.tools' has no attribute 'TOOLS'` |
| `"funtion": {...}` | `"function": {...}` | HTTP 422 `tools[1]: missing field 'function'` |
| `"promperties"` / `"promerties"` | `"properties"` | 不报错，但模型看不到参数定义（静默失效） |
| `" ".json(args.question)` | `" ".join(...)` | `AttributeError: 'str' object has no attribute 'json'` |
| `json.dump(...)` 写文件 | `json.dumps(...)` | `TypeError: dump() missing 1 required positional argument: 'fp'` |
| `message.append(...)` | `messages.append(...)` | `AttributeError: 'dict' object has no attribute 'append'` |
| `"completion_token"` | `"completion_tokens"` | 不报错，但 token 统计**永远是 0** |

**教训与对策**：

1. **数据字面量配一条本地断言**，把拼写错误在校验阶段暴露（成本 0 秒、0 token）：
   ```python
   assert all(t["type"] == "function" and "function" in t for t in TOOLS)
   assert all("properties" in t["function"]["parameters"] for t in TOOLS)
   ```
2. **用假模型测循环逻辑**：把 `llm.chat` 替换成假函数，验证「2 次调用、2 步、answered」，不花一分钱。真跑出问题时，就能先排除循环逻辑。
3. **分段验证**：配置 → 工具（本地可测）→ 循环（假模型可测）→ 整链路（真模型）。每段单独跑通再串联，报错才指得准。

---

## 10. 下一步

1. **多轮对话**（阶段一验收项）：让 `run_agent` 接受外部 `messages` 历史，加 `--chat` REPL；顺带处理历史膨胀（保留最近 N 轮）。
2. **流式输出**（阶段一验收项）。
3. **补 q21 / q22** 两个「易传错参数」样本，验证参数描述的作用。
4. **答案正确性评测**：现在只测工具选择，第 6 周补 LLM-as-a-Judge。
5. **`max_steps` 触发率监控**：作为生产环境的健康指标，突然升高通常意味着工具批量报错或提示词失配。
