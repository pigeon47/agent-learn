# 第 5 周 · 记忆与状态管理（长期事实记忆 + 短期上下文压缩）

给助手加两层记忆：

- **长期记忆**：sqlite3 存「用户偏好与事实」，跨进程/跨会话持久化，下次启动仍生效
- **短期记忆**：会话历史 + 超阈值时用 LLM 摘要压缩早期对话，控制 prompt 增长

全流程零第三方依赖（标准库 `sqlite3` + 复用第 3 周的 LLM 调用层）。

**核心数据**

| 指标 | 无记忆 | 有记忆 |
|---|---|---|
| 总准确率（10 题） | 40.0% | **100.0%** |
| 需记忆题准确率（8 题） | 25.0% | **100.0%** |
| 平均 prompt tokens | 24 | 128 |

| 短期记忆压缩（6 轮对话） | 无压缩 | 有压缩 | 变化 |
|---|---|---|---|
| prompt token 合计 | 10,731 | **5,261** | **−51.0%** |
| 第 6 轮单轮 prompt | 3,083 | **462** | −85% |

---

## 1. 快速开始

```powershell
cd E:\agent-learn\week05_memory

# ① 记忆库自测（0 成本）
E:\agent-learn\env\python.exe -m mem.store

# ② 抽取自测：从一句话里抽「值得记住的事实」（3 次调用）
E:\agent-learn\env\python.exe -m mem.extract

# ③ 多轮对话（带记忆 + 压缩）
E:\agent-learn\env\python.exe -m mem --chat --session demo

# ④ 查看/清空某个会话的记忆（0 成本）
E:\agent-learn\env\python.exe -m mem --memory --session demo
E:\agent-learn\env\python.exe -m mem --reset  --session demo

# ⑤ 有/无记忆 A/B 评测（20 次调用）
E:\agent-learn\env\python.exe -m mem --eval

# 其他开关
#   --no-memory     关闭长期记忆（对照组）
#   --no-compress   关闭短期压缩
#   --max-turns 4   超过 4 轮触发压缩
```

必须用 `-m mem` 运行（包内相对导入）。Key 复用 `week01_llm_client/.env`。

---

## 2. 目录结构与模块职责

```
week05_memory/
├── mem/
│   ├── __init__.py      包的标记
│   ├── store.py         sqlite 记忆库：表结构、upsert / get / all / search / as_prompt
│   ├── extract.py       从一轮问答抽「值得记住的事实」（LLM + JSON + 格式校验）
│   ├── chat.py          主流程：注入记忆 → 回答 → 回写事实；含 compress_history()
│   ├── evaluate.py      10 题 × 有/无记忆 A/B
│   └── __main__.py      CLI：--chat / --memory / --reset / --eval
├── data/
│   ├── memory.db        运行时生成
│   └── eval_memory.jsonl  10 条测试题（8 条需记忆 + 2 条对照）
└── results/
    ├── eval_memory.csv        A/B 明细（20 行）
    └── compress_compare.csv   压缩前后每轮 token
```

---

## 3. 数据流

```
用户提问
   │
   ├─ 短期记忆：history（最近若干轮原文）
   │
   ├─ 长期记忆：memory.as_prompt(question)
   │     记忆条数 ≤ 20 → 全量注入；> 20 → 关键词检索取 top-5
   │
   ▼
[system: 人设 + 已知信息] + history + [user: 本轮问题]
   │
   ▼
LLM 回答
   │
   ├─ extract_facts(问题, 回答) → [{"key","value"}] → memory.upsert()  ← 写回 sqlite
   │
   └─ history 追加本轮问答
          │
          └─ 若 len(history) ≥ max_turns*2 → compress_history()：早期对话 → 一条摘要
```

---

## 4. 关键设计决策

### 4.1 长期记忆为什么用 sqlite3 而不是向量库

| | sqlite3 | 向量库 |
|---|---|---|
| 依赖 | 标准库自带 | 需装 sentence-transformers 或调 embedding API |
| 记忆量 | 几千条以内足够 | 上万条才有优势 |
| 查询 | SQL（按 key/session/时间） | 语义相似度 |

本周记忆量是"几条到几十条"，sqlite 完全够用。**语义检索留到记忆量真正变大之后**。

### 4.2 存储粒度：只存「键值对事实」

```python
name            = 张伟
learning_goal   = 12 周内做出可部署的 AI Agent 系统
response_style  = 简洁，不要用表情符号
```

不存整段对话。理由：体积小、可去重（`UNIQUE(session, key)`）、可审计（能直接列出"我知道你什么"）、易评测。

### 4.3 为什么记忆注入用「全量」而不是「检索」

**初版用关键词重合度检索，实测完全失效**：

```
查询「我叫什么名字」
  查询 token: ['我','叫','什','么','名','字','我叫','叫什','什么','么名','名字']
  name             重合 token=[]
  preference_style 重合 token=[]
  learning_goal    重合 token=[]
```

存的是 `name=张伟`，用户问的是"名字"——字面完全不重叠。

**改为**：记忆条数 ≤ 20 时全量注入（召回率 100%，几百 token 可接受）；超过 20 条才退回关键词检索。

### 4.4 事实抽取要过「格式闸门」

```python
_KEY_RE = re.compile(r"^[a-z0-9_]{2,32}$")   # key 只能是 2~32 个小写字母/数字/下划线
if _KEY_RE.match(key) and value:
    facts.append({"key": key, "value": value[:200]})
```

模型可能返回 `"Name"`、`"用户名字"`、`"my-key"` 这类不合规 key，直接拒绝，保证写进库的 key 永远是干净标识符——这也是 `UNIQUE(session, key)` 去重能成立的前提。

### 4.5 会话隔离靠一个字段

```sql
UNIQUE(session, key)      -- 同一会话同一个 key 只有一条 → "改名"是更新，不是新增
```

`Memory(session="alice")` 与 `Memory(session="bob")` 天然互不可见，一条 SQL 就够，不需要多个数据库文件。

---

## 5. 实验结果

### 5.1 有/无记忆 A/B（10 题，8 条需记忆）

| 组 | n | 总准确率 | 需记忆题准确率 | 平均 prompt |
|---|---|---|---|---|
| 无记忆 | 10 | 40.0% | 25.0% | 24 |
| 有记忆 | 10 | **100.0%** | **100.0%** | 128 |

典型对照（`m01 我叫什么名字？`）：

- 无记忆：「我不知道你的名字，因为你还没有告诉我。」
- 有记忆：「你叫张伟。」

**代价**：平均 prompt 从 24 → 128 token（多 104）。用 100 token 换 75 个百分点的准确率，非常划算。

### 5.2 短期记忆压缩（6 轮对话，`max_turns=2`）

| 轮次 | 无压缩 | 有压缩 | 节省 |
|---|---|---|---|
| 1 | 37 | 37 | 0 |
| 2 | 485 | 390 | +95 |
| 3 | 1547 | 1187 | +360 |
| 4 | 2715 | 1917 | +798 |
| 5 | 2864 | 1268 | +1596 |
| 6 | 3083 | **462** | **+2621** |
| **合计** | **10,731** | **5,261** | **−51.0%** |

无压缩时 prompt 随轮次线性增长（每轮 +300~800）；有压缩时稳定在 400~1200。

---

## 6. 踩坑记录

本周的 bug 几乎全是"看着能跑但静默失效"型，值得单独记：

| 坑 | 现象 | 原因 |
|---|---|---|
| `self.bd_path` | `AttributeError: ... has no attribute 'bd_path'` | db 打成 bd |
| `self.conn.conmmit()` | 插入不生效 | commit 打成 conmmit |
| `x[1]["updata_at"]` | `KeyError: 'updata_at'` | updated_at 打成 updata_at |
| **`_KEY_RE` 少了 `_`** | 抽取只返回 `name`，`learning_goal`/`response_style` 全被丢弃 | 正则 `[a-z0-9]` 漏了下划线，**模型抽对了，是校验把它丢了** |
| `data.get("fact", [])` | 抽取永远返回 `[]` | 少个复数 s，`.get` 静默返回默认值 |
| `llm.caht(...)` | `AttributeError: module ... has no attribute 'caht'` | chat 打成 caht |
| `{"answe": ...}` | `KeyError: 'answer'` | 返回字典键名拼错 |
| `return` 缩进 4 格 | 循环后的代码整段变灰（unreachable） | `return` 写在了 `if` 外面 |
| **`mem.close()`/`return rows` 在 for 循环内** | 评测每组只跑第 1 题 | 缩进错误，且不报错——只是"结果变少" |
| `PROJECT` 多一层 / `_ROOT` 少一层 | `FileNotFoundError: E:\agent-learn\data\eval_memory.jsonl` | 两个路径常量写反了 |

**结论**：`KeyError` / `AttributeError` 是好事（立刻暴露）；真正危险的是
`.get(默认值)`、正则校验、缩进这类**静默失效**——所以每次改完都跑一次零成本自测
（`-m mem.store`、`-m mem.extract`），能在写下一个文件前拦住 3 个拼写错。

---

## 7. 已知局限与下一步

| 局限 | 说明 |
|---|---|
| 关键词检索不可用 | 记忆超过 20 条后，`search()` 靠字面重合，对自然语言提问召回率低（实测「我叫什么名字」与 `name=张伟` 重合为 0） |
| 无记忆淘汰 | `hits` 计数只累加，没有"长期未用就删除"策略 |
| 抽取靠 LLM | 每次对话多一次调用；模型偶尔漏抽，可改规则 + LLM 混合 |
| 无冲突检测 | 用户改口（"我不叫张伟了"）靠 `upsert` 覆盖，但不提示矛盾 |
| 摘要会丢细节 | 压缩后早期具体数值可能模糊（压缩的固有代价） |

**下一步**

1. 记忆量大后用**向量检索**（embedding + 余弦相似度），替换关键词检索
2. 加**淘汰策略**：按 `hits` 与 `updated_at` 清理长期不用的记忆
3. 加**冲突检测**：新事实与旧事实语义矛盾时提示用户确认
4. 记忆管理做成独立子命令（`--memory add/del/search`）

---

## 8. 与第 3、4 周的关系

| 周 | 复用点 |
|---|---|
| 第 3 周 | `llm.chat()`（超时/错误处理）、`config.load_env()` |
| 第 4 周 | 「先切分再检索」的思路——长期记忆是"以事实为单位的切分"，短期压缩是"以轮次为单位的切分" |
| 第 5 周新增 | 持久化（sqlite）、事实抽取（LLM 结构化输出 + 格式校验）、上下文压缩（滚动摘要） |

能力链路：**会调接口（1）→ 会写提示词（2）→ 会调工具（3）→ 会让模型基于资料回答（4）→ 会让模型记住你（5）**。
