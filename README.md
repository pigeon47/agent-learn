# agent-learn

AI Agent 学习项目 —— 按《AI Agent 学习路线（3 个月）》12 周计划，从零构建可用的 AI Agent 系统。

## 当前进度
- 2026-10-09 学会环境配置与Git基础
- [x] 第 1 周 · Python 工程化与 API 调用：环境搭建
- [ ] 后续周次按路线推进

## 环境

- Python 3.12.15（conda 环境，位于项目目录 `env/` 下，已被 .gitignore 排除出仓库）
- pip 使用清华镜像源，缓存目录在 E:\caches\pip
- VSCode 解释器选择 `env\python.exe`（见 .vscode/settings.json）

## 目录结构

```
agent-learn/
├── test_env.py    # 环境自检脚本（解释器 / 版本 / httpx 三连检）
├── .vscode/       # 解释器与运行配置（保留在仓库中，便于他人复现）
└── .gitignore     # 排除 env/、.env 密钥、模型权重等
```

## 四阶段路线

1. **阶段一（第 1–3 周）**：Python 工程化 + LLM 基础 + Prompt → 命令行助手
2. **阶段二（第 4–6 周）**：单 Agent 核心 —— 工具调用、ReAct、RAG、记忆、评测
3. **阶段三（第 7–9 周）**：框架与多智能体 —— LangGraph、CrewAI、MCP、可观测性
4. **阶段四（第 10–12 周）**：部署、成本、安全、专项 → 毕业项目上线
