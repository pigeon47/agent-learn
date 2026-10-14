# week01_llm_client

第 1 周实战项目：把"配置管理 + 日志 + httpx + 异步重试"组装成一个规范的 Python 包。

对应《AI Agent 学习路线》第 1 周：

> 学习目标：能写出结构清晰、可复用、能处理异常和超时的 LLM 调用代码。

---

## 目录说明

```
week01_llm_client\
├─ .env                     ← 你的真实 Key（自己创建，绝不提交）
├─ .env.example             ← 模板，进 Git
├─ requirements.txt
├─ README.md
├─ llm_client\              ← 包（本周主角）
│   ├─ __init__.py          ← 对外暴露 Settings 和 LLMClient
│   ├─ config.py            ← 配置：读 .env、缺 Key 立刻报错、密钥脱敏
│   ├─ logger_setup.py      ← 日志：控制台 + 文件双输出
│   └─ client.py            ← 核心：LLMClient（★ 你要实现的部分）
├─ scripts\                 ← 可执行脚本
│   ├─ demo_call.py         ← 环境冒烟测试（已写好，可直接跑）
│   ├─ demo_concurrent.py   ← 必做 2：并发 + 参数对比（★ 你要实现的部分）
│   └─ check_secrets.py     ← 加分项：密钥扫描（★ 你要实现的部分）
└─ logs\                    ← 自动生成，已被 .gitignore 忽略
```

★ 标记的三个地方是需要你自己写的，其余都是可直接使用的现成代码。

---

## 一、安装与配置

```powershell
cd E:\agent-learn\week01_llm_client

# 1. 装依赖（httpx 通常已装，python-dotenv 需要装）
..\env\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2. 复制模板并填 Key
Copy-Item .env.example .env
notepad .env
```

`.env` 里需要填的内容：

```env
DEEPSEEK_API_KEY=sk-你的真实key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
DEEPSEEK_TIMEOUT=60
```

> Key 在 https://platform.deepseek.com/api_keys 申请。
> 练手一律用 `deepseek-flash`（便宜的那个），别用 `deepseek-v4-pro`。

---

## 二、运行方式（⚠️ 必须这样写）

**永远站在项目根目录，用 `-m` 方式运行：**

```powershell
cd E:\agent-learn\week01_llm_client

..\env\python.exe -m scripts.demo_call          # 环境冒烟测试
..\env\python.exe -m scripts.demo_concurrent    # 必做 2
..\env\python.exe -m scripts.check_secrets      # 加分项
```

**为什么不能用 `python scripts\demo_call.py`？** 因为那样 Python 只会把 `scripts\` 加进搜索路径，找不到同级的 `llm_client` 包，会报：

```
ModuleNotFoundError: No module named 'llm_client'
```

这是 Python 新手第一号坑，你自己踩一次就记住了。

---

## 三、本周任务清单

### 必做 1：实现 LLMClient（`llm_client\client.py`）

四项能力，一项都不能少：

- [x] **超时**：四类超时分别设置，`read` 用 `.env` 里的 `DEEPSEEK_TIMEOUT`
- [x] **指数退避重试**：失败后 `0.5 → 1 → 2` 秒再试，最多 3 次
- [x] **日志**：每次调用记录模型名、token 用量、是否重试；重试用 WARNING，最终失败用 ERROR
- [x] **token 统计**：累加 `usage.total_tokens`，包含 `reasoning_tokens`

**关键区分（面试常问）**：

| 异常 | 该重试吗 |
|---|---|
| `httpx.ConnectError`、`httpx.TimeoutException` | ✅ 重试 |
| `HTTPStatusError` 429 / 5xx | ✅ 重试 |
| `HTTPStatusError` 400 / 401 / 403 | ❌ **不重试**（请求本身有问题） |

### 必做 2：并发 + 参数对比（`scripts\demo_concurrent.py`）

- [ ] 用 `asyncio.Semaphore(5)` 限流，并发跑一批请求
- [ ] **temperature 对比**：`thinking` 关闭，试 `0 / 0.7 / 1.0 / 1.5 / 2.0`，每个温度调 2 次，看输出稳不稳定
- [ ] **reasoning_effort 对比**：`thinking` 开启，试 `none / low / high / max`，记录耗时和思考 token
- [ ] 结果写成 markdown 表格存到 `temperature_compare.md`

> ⚠️ **坑**：官方文档明确写了 temperature **在思考模式下无效**（"Has no effect in thinking mode"）。所以做 temperature 实验**必须**传 `thinking: {"type": "disabled"}`，否则 5 次结果几乎一模一样，你会以为是参数没生效。

### 必做 3：确认仓库里搜不到密钥

```powershell
cd E:\agent-learn
git grep -i "sk-" $(git rev-list --all)     # 没有输出才算过关
git log -S"sk-" --oneline                    # 同样应该没有输出
```

### 加分项：密钥扫描脚本（`scripts\check_secrets.py`）

- [ ] 递归扫描项目里的 `.py/.md/.json/.txt/.yml` 文件
- [ ] 用正则匹配 `sk-[A-Za-z0-9]{16,}` 和 `api_key = "..."` 之类
- [ ] 命中就打印"文件:行号"，退出码设为 1
- [ ] 挂到 git 钩子：`.git/hooks/pre-commit` 里写 `python -m scripts.check_secrets || exit 1`

---

## 四、验收标准

本周结束时你应该能做到：

- [ ] `python -m scripts.demo_call` 成功返回模型回答，并打印 token 用量
- [ ] `python -m scripts.demo_concurrent` 输出对比表格，且 temperature 不同时输出明显不同
- [ ] 故意把 base_url 改错 → 日志里出现 WARNING 重试，最终抛 `ConnectError`
- [ ] 故意把 `DEEPSEEK_TIMEOUT` 设成 0.1 → 出现 `ReadTimeout`
- [ ] 故意把 Key 改错 → 出现 ERROR 401，**且只报一次（没有重试）**
- [ ] `git status` 里看不到 `.env`，但能看到 `.env.example`
- [ ] 两条 `git grep` 自查命令都无输出
- [ ] 至少 5 次有意义的 commit（`feat:` / `fix:` / `docs:` 开头）

---

## 五、常见报错速查

| 报错 | 原因 | 解决 |
|---|---|---|
| `ModuleNotFoundError: No module named 'llm_client'` | 站错目录或用文件路径跑 | 在项目根目录用 `-m` |
| `RuntimeError: 缺少环境变量 DEEPSEEK_API_KEY` | 没建 `.env` 或没填 Key | `Copy-Item .env.example .env` 后填上 |
| `httpx.ReadTimeout` 频繁出现 | 超时太短 | `.env` 里把 `DEEPSEEK_TIMEOUT` 调大（60 或 120） |
| `HTTPStatusError: 401` | Key 不对 | 检查 `.env`，注意别把引号也复制进去 |
| `HTTPStatusError: 402` | 余额不足 | 去平台充值（这套练习花费极低） |
| `UnicodeEncodeError: 'gbk' codec` | 日志里用了 emoji | 别在日志里用 emoji，或设 `$env:PYTHONUTF8=1` |
| 日志每行打印两遍 | 重复添加了 handler | `setup_logger` 里已有防重复逻辑，检查是不是自己又加了一层 |
