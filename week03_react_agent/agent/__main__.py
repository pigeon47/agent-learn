"""入口：python -m agent "你的问题"   或   python -m agent --eval"""
from __future__ import annotations

import argparse
import csv
import json

from . import config, loop



def print_run(result: dict) -> None:
    """把一次运行的过程打印成人能读的样子。"""
    for item in result["trace"]:
        if item["type"] == "tool_call":
            flag = "OK" if item["ok"] else "ERR"
            print(f"[{flag}]第{item['step']}步 调用{item['tool']}({item['arguments']})")
            print(f"         → {item['result'][:120]}")
        elif item["type"] == "answer":
            print(f" [ANS]第 {item['step']} 步 最终答案: {item['content'][:200]}")
    u = result["usage"]
    print(f" 步数={result['steps']} 工具={result['tools_used']} "
          f"token={u['prompt_tokens']}+{u['completion_tokens']} 结束原因={result['stopped']}")

def run_eval(cfg: dict, max_steps: int) -> None:
    """跑 data/eval_questions.jsonl, 统计工具选择准确率, 写 results/eval.csv。"""
    qfile = config.PROJECT_DIR / "data" / "eval_questions.jsonl"
    questions = [json.loads(line) for line in
                 qfile.read_text(encoding="utf-8").splitlines() if line.strip()]

    rows = []
    for q in questions:
        result = loop.run_agent(cfg, q["question"], max_steps=max_steps)
        got = result["tools_used"][0] if result["tools_used"] else "none"
        ok = int(got == q["expect_tool"])
        rows.append({
            "id": q["id"],
            "question": q["question"],
            "got_tool": got,
            "ok": ok,
            "steps": result["steps"],
            "prompt_tokens": result["usage"]["prompt_tokens"],
            "completion_tokens": result["usage"]["completion_tokens"],
        })
        print(f" {q['id']} 期望={q['expect_tool']:12s} 实际={got:12s} {'✓' if ok else '✗'} 步数={result['steps']}")

    out_dir = config.PROJECT_DIR / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "eval.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    hit = sum(r["ok"] for r in rows) / len(rows) * 100
    print(f"\n工具选择准确率: {hit:.1f}% ({sum(r['ok'] for r in rows)}/{len(rows)})")
    print(f"明细已写入: {out}")

def main() -> None:
    parser = argparse.ArgumentParser(description="手写 ReAct Agent")
    parser.add_argument("question", nargs="*", help="要问 Agent 的问题")
    parser.add_argument("--eval", action="store_true", help="跑测试集, 统计工具选择准确率")
    parser.add_argument("--max-steps", type=int, default=6)
    args = parser.parse_args()

    config.load_env()
    cfg = config.settings()

    if args.eval:
        run_eval(cfg, args.max_steps)
        return

    question = " ".join(args.question).strip() or input("问题: ")
    print(f"\n[问题] {question}")
    result = loop.run_agent(cfg, question, max_steps=args.max_steps)
    print_run(result)

    out_dir = config.PROJECT_DIR / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    with(out_dir / "trace.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"question": question, **result}, ensure_ascii=False) + "\n")



if __name__ == "__main__":
    main()
        