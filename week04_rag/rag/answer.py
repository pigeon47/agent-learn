r"""第4周 · RAG 问答：检索top-k → 拼接上下文 → 带引用回答; 资料不足则拒答。

用法：
    cd E:\agent-learn\week04_rag
    E:\agent-learn\env\python.exe -m rag.answer "asyncio 的 gather 怎么用"
    E:\agent-learn\env\python.exe -m rag.answer          # 交互模式
"""
from __future__ import annotations

import sys
from pathlib import Path

# 让 E:\agent-learn 进入 sys.path，才能复用 week03 的包
_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from week03_react_agent.agent import config as llm_config   # noqa: E402
from week03_react_agent.agent import llm                    # noqa: E402

from .chunking import load_corpus                           # noqa: E402
from .index import BM25                                     # noqa: E402

REFUSAL = "资料中没有相关内容"

SYSTEM_PROMPT = """你是严谨的文档问答助手，只能依据用户提供的资料回答。

规则：
1. 只能使用资料里的信息，不得引入外部知识，也不要凭印象补充。
2. 每个要点的末尾必须标注来源，格式：[文件名 > 标题路径]。
3. 如果资料不足以回答问题，只输出这一句：资料中没有相关内容。
4. 不要编造资料里没有的数字、名称、链接或结论。
5. 用中文回答，简洁，不超过 200 字。
6. 多份资料表达同一件事时，只保留最准确的一处，不要重复陈述。

输出格式：
- 每个要点单独一行，以「- 」开头，一个要点只讲一件事。
- 直接用要点陈述，不要写"另外""此外""同时""需要注意的是"这类过渡词。
- 要点按重要性排序，最重要的放第一条。
"""



# ------------------------------------------------------------------ 检索与拼装
def retrieve(index: BM25, question: str, top_k: int = 3) -> list[tuple[float, dict]]:
    """检索 top-k 相关块 (已启用停用词过滤)。"""
    return index.search(question, top_k=top_k, drop_stopwords=True)



def build_context(hits: list[tuple[float, dict]]) -> str:
    """把检索结果拼成带编号的资料块，交给模型。"""
    blocks = []
    for i,(_score, c) in enumerate(hits, 1):
        blocks.append(f"[{i}] ({c['doc']} > {c['heading']}) \n{c['text']}")
    return "\n\n".join(blocks)



# ------------------------------------------------------------------ 问答主流程
def answer(cfg: dict, index: BM25, question: str, top_k: int = 3) -> dict:
    """返回 {answer, refused, hits, usage, reason}。"""
    hits = retrieve(index, question, top_k)
    if not hits:
        return {"answer": REFUSAL, "refused": True, "hits": [],
                "usage": {}, "reason": "检索无命中"}

    info = index.analyze_query(question)
    if not info["known"]:
        return {"answer": REFUSAL, "refused": True, "hits": hits,
                "usage": {}, "reason": f"查询词全部不在知识库：{info['missing']}"}

    context = build_context(hits)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"资料：\n{context}\n\n问题：{question}"},
    ]
    message, usage = llm.chat(cfg, messages)
    text = (message.get("content") or "").strip()
    refused = REFUSAL in text or len(text) < 4 
    return {"answer": text, "refused": refused, "hits": hits,
            "usage": usage, "reason":"模型判断资料不足" if refused else ""}

def show(cfg: dict, index:BM25, question: str, top_k: int = 3) -> dict:
    """跑一次并打印成人能读的样子。"""
    r = answer(cfg, index, question, top_k)
    print(f"\n问题：{question}")
    print(f"回答：{r['answer']}")
    if r["refused"]:
        print(f" (拒答原因：{r['reason']})")
        return r
    print("\n资料来源：")
    for i, (score, c) in enumerate(r["hits"], 1):
        print(f" [{i}] {score:6.2f} {c['doc']} > {c['heading']}")
    u = r["usage"]
    print(f"\ntoken: {u.get('prompt_tokens', 0)} + {u.get('completion_tokens', 0)}")
    return r



# ------------------------------------------------------------------ CLI
def main() -> None:
    llm_config.load_env()
    cfg = llm_config.settings()
    index = BM25(load_corpus(size=512))
    print(f"知识库就绪：{index.N} 块，平均 {int(index.avg_len)} 词元")

    question = " ".join(sys.argv[1:]).strip()
    if question:
        show(cfg, index, question)
        return

    print("交互模式, 输入 exit 退出。")
    while True:
        try:
            q = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if q.lower() in {"exit", "quit", "q"}:
            break
        if not q:
            continue
        show(cfg, index, q)


if __name__ == "__main__":
    main()
