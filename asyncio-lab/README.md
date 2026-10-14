# asyncio-lab

第 1 周 · Python 工程化（asyncio 部分）的练习代码。

讲义：`E:\code\Python asyncio 实战讲义.docx`（6 个递进版本 + 9 个坑 + 7 道练习与答案）

## 怎么运行

用本项目自带的解释器（Python 3.12.15，位于 `E:\agent-learn\env`）：

```powershell
cd E:\agent-learn\asyncio-lab

..\env\python.exe lab.py v0      # 版本 0：同步，约 5 秒
..\env\python.exe lab.py v2      # 版本 2：gather 并发，约 1 秒
..\env\python.exe ex1.py         # 练习 1
```

也可以先激活环境再跑（效果一样）：

```powershell
conda activate E:\agent-learn\env
python lab.py v0
```

`lab.py` 用参数选版本：`v0` `v1` `v2` `v3` `v4` `v5`。

Python 3.12 支持讲义里全部示例，包括 `TaskGroup`、`asyncio.timeout`、`except*`。

## 文件说明

```
asyncio-lab\
├─ lab.py            # 6 个版本的实验骨架，自己往里填代码
├─ ex1.py ~ ex7.py   # 7 道练习，自己创建
├─ notes.md          # 耗时与踩坑记录（这是你的实验证据）
├─ requirements.txt  # 依赖清单，今天用不到
└─ .env.example      # 密钥模板
```

## 关于 .env（现在还用不到）

`.env` 是**文件**不是文件夹，里面一行一个密钥：

```
OPENAI_API_KEY=sk-xxxxxxxx
```

代码里这样读：

```python
import os
from dotenv import load_dotenv

load_dotenv()
key = os.environ["OPENAI_API_KEY"]
```

三条铁律：

1. `.env` 永远不提交（仓库根目录的 `.gitignore` 已经排除它，并且用 `!.env.example` 放行了模板文件）。
2. 提交的是 `.env.example`：只有键名、值是占位符。
3. 今天的 asyncio 练习全是本地模拟，**不需要任何密钥，所以现在不用建 `.env`**。

## 做完之后记得提交

```powershell
cd E:\agent-learn
git status
git add asyncio-lab
git commit -m "feat: 第1周 asyncio 练习（6 个版本 + 练习题）"
```

提交前顺手确认 `git status` 里没有 `env/`、`.env`、`__pycache__/` 这些不该进仓库的东西。
