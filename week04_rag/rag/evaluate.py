r"""第四周 · 检索评测：三档 chunk 大小下的 Recall@1/ Recall@2 / Recall@3 / MRR.

用法：
    cd E:\agent-learn\week04_rag
    E:\agent-learn\env\python.exe -m rag.evaluate

纯检索评测，不调用LLM，零成本。
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .chunking import load_corpus
from .index import BM25

PROJECT = Path(__file__).resolve().parent.parent
DATA = PROJECT / "data"
RESULTS = PROJECT / "results"



def load_questions() -> list[dict]:
    path = DATA / "eval_questions.jsonl"
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]

def rank_of_expected(hits: list[tuple[float, dict]], expect_doc: str) -> int:
    """命中期望文档的最小名次；没命中返回 0。"""
    for rank, (_score, c) in enumerate(hits, 1):
        if c["doc"] == expect_doc:
            return rank
    return 0

def evaluate_one(build_chunks, questions: list[dict], label: str,
                 top_k: int = 3) -> tuple[list[dict], dict]:
    index = BM25(build_chunks())
    rows = []
    for q in questions:
        if q["expect_doc"] == "NONE":
            continue
        hits = index.search(q["question"], top_k=top_k, drop_stopwords=True)
        rank = rank_of_expected(hits, q["expect_doc"])
        rows.append({
            "config": label,
            "id": q["id"],
            "question": q["question"],
            "expect_doc": q["expect_doc"],
            "top1_doc": hits[0][1]["doc"] if hits else "",
            "top1_score": round(hits[0][0], 2) if hits else 0,
            "rank": rank,
            "hit@1": int(rank == 1),
            "hit@3": int(1 <= rank <= 3),
        })
    n = len(rows)
    summary = {
        "config": label,
        "n": n,
        "recall@1": round(sum(r["hit@1"] for r in rows) / n * 100, 1),
        "recall@3": round(sum(r["hit@3"] for r in rows) / n * 100, 1),
        "mrr": round(sum((1 / r["rank"] if r["rank"] else 0 for r in rows)) / n, 3),
    }
    return rows, summary

def check_refusal(build_chunks, questions: list[dict], label: str)  -> None:
    """拒答测试集：库里没有的问题，看检索侧有没有'缺失实体'信号。"""
    index = BM25(build_chunks())
    print(f"\n---拒答信号({label})---")
    for q in questions:
        if q["expect_doc"] != "NONE":
            continue
        info = index.analyze_query(q["question"])
        hits = index.search(q["question"], top_k=3, drop_stopwords=True)
        top = f"{hits[0][0]:.2f} {hits[0][1]['doc']}" if hits else "无命中"
        flag = "有缺失实体" if info["missing"] else "无缺失信号"
        print(f" {q['id']} {q['question']}")
        print(f"    库中缺失={info['missing']} -> {flag} | top1={top}")

def main() -> None:
    questions = load_questions()
    n_refuse = sum(1 for q in questions if q["expect_doc"] == "NONE")
    print(f"评测集：{len(questions)} 条 (其中拒答题 {n_refuse} 条)")

    all_rows, summaries = [], []
    for size in (256, 512, 1024):
        label = f"size={size}"
        print(f"\n=== {label} ===")
        rows, summary = evaluate_one(lambda s = size: load_corpus(size=s), questions, label)
        all_rows.extend(rows)
        summaries.append(summary)
        print(f" Recall@1={summary['recall@1']}% "
              f"Recall@3={summary['recall@3']}% MRR={summary['mrr']}")
        miss = [r["id"] for r in rows if not r["hit@3"]]
        if miss:
            print(f" top-3 未命中: {miss}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "eval.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\n明细已写入：{out}")

    print("\n=== 三档对比 ===")
    print(f"{'配置':<12}{'n':>}{'Recall@1':>10}{'Recall@3':>10}{'MRR':>8}")
    for s in summaries:
        print(f"{s['config']:<}{s['n']:>4}{s['recall@1']:>10}"
              f"{s['recall@3']:>10}{s['mrr']:>8}")

    check_refusal(lambda: load_corpus(size=512), questions, "size=512")

if __name__ == "__main__":
    main()
