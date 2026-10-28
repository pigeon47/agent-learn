r"""10 题 × 有/无记忆 A/B 对比。

有记忆组：先写入 8 条事实，再问；
无记忆组：同一个空库，同样的问题。
判定：回答里是否包含期望关键词。
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from week03_react_agent.agent import config as llm_config   # noqa: E402

from .chat import ask                                       # noqa: E402
from .store import Memory                                   # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent          # week05_memory

SEED_FACTS = {
    "name": "张伟",
    "learning_goal": "12 周内做出可部署的 AI Agent 系统",
    "response_style": "简洁，不要用表情符号",
    "current_week": "第 5 周，正在学习记忆化与状态管理",
    "model": "deepseek-flash",
    "workspace": "E:\\agent-learn",
    "python_env": "E:\\agent-learn\\env\\python.exe",
}



def load_questions() -> list[dict]:
    path = PROJECT / "data" / "eval_memory.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

def hit(answer: str, expects: list[str]) -> bool:
    """回答里是否包含全部期望关键词（不区分大小写）。"""
    low = answer.lower()
    return all(e.lower() in low for e in expects)

def run_group(cfg: dict, questions: list[dict], use_memory: bool) -> list[dict]:
    session = "eval_mem" if use_memory else "eval_nomem"
    mem = Memory(session=session)
    mem.forget()
    if use_memory:
        for k, v in SEED_FACTS.items():
            mem.upsert(k, v)

    rows = []
    for q in questions:
        r = ask(cfg, mem, q["question"], use_memory=use_memory, do_extract=False)
        ok = hit(r["answer"], q["expect"])
        rows.append({
            "group": "with_memory" if use_memory else "no_memory",
            "id": q["id"],
            "needs_memory": q["needs_memory"],
            "expect": "/".join(q["expect"]),
            "ok": int(ok),
            "answer": r["answer"][:60].replace("\n", " "),
            "prompt_tokens": r["usage"].get("prompt_tokens", 0),
            "completion_tokens": r["usage"].get("completion_tokens", 0),
        })
        print(f"  [{'OK ' if ok else 'NG '}] {q['id']} {q['question'][:24]} -> {r['answer'][:40]}")
    mem.close()
    return rows



def main() -> None:
    llm_config.load_env()
    cfg = llm_config.settings()
    questions = load_questions()
    print(f"评测集：{len(questions)} 条 (需记忆 {sum(1 for q in questions if q['needs_memory'])} 条)")

    all_rows = []
    summaries = []
    for use_memory in (False, True):
        label = "有记忆" if use_memory else "无记忆"
        print(f"\n=== {label} ===")
        rows = run_group(cfg, questions, use_memory)
        all_rows.extend(rows)
        n = len(rows)
        ok = sum(r["ok"] for r in rows)
        mem_rows = [r for r in rows if r["needs_memory"]]
        mem_ok = sum(r["ok"] for r in mem_rows)
        summaries.append({
            "group": label,
            "n": n,
            "accuracy": round(ok / n * 100, 1),
            "mem_accuracy": round(mem_ok / len(mem_rows) * 100, 1) if mem_rows else 0.0,
            "avg_prompt_tokens": round(sum(r["prompt_tokens"] for r in rows) / n),
        })

    out_dir = PROJECT / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "eval_memory.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\n明细已写入：{out}")

    print("\n=== 对比 ===")
    print(f"{'组':<8}{'n':>4}{'总准确率':>10}{'需记忆题准确率':>16}{'平均prompt':>12}")
    for s in summaries:
        print(f"{s['group']:<8}{s['n']:>4}{s['accuracy']:>10}"
              f"{s['mem_accuracy']:>16}{s['avg_prompt_tokens']:>12}")

if __name__=="__main__":
    main()