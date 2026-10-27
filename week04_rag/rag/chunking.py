"""把 Markdown 切成可检索的小块，每块记住⌈来自哪个文那个标题路径⌋。

为什么要保留 heading:
    答案里要写 ⌈引用来源⌋ ，光有文件名不够，用户要知道是文档的哪一节。
"""
from __future__ import annotations

import re
from pathlib import Path

_PROJECT = Path(__file__).resolve().parent.parent
DATA_DIR = _PROJECT / "data"



def _find_cut(text: str, size: int, window: int = 80) -> int:
    """在 [size-window, size] 里找最自然的断点（换行/句号/空格…），找不到就硬切。

    目的：避免把 "Task.result" 切成 "Task.res" 这种半截词。
    """
    lo = max(size - window, 1)
    for sep in ("\n", "。", "！", "？", "；", ";", "，", ",", " "):
        pos = text.rfind(sep, lo, size)
        if pos != -1:
            return pos + 1          # 断在分隔符之后
    return size                     # 实在找不到就按原长度硬切


def _split_long(text: str, size: int, overlap: int) -> list[str]:
    """超长正文按段落累积切块；块之间保留 overlap 个字符的尾部重叠，避免切断上下文。"""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paras:
        if len(buf) + len(p) + 2 <= size:
            buf = f"{buf}\n\n{p}" if buf else p
            continue
        if buf:
            chunks.append(buf)
        while len(p) > size:
            cut = _find_cut(p, size)
            chunks.append(p[:cut])
            start = max(cut - overlap, 1)    # 保证 start 为正，避免切片包回开头
            p = p[start:]
        buf = p
    if buf:
        chunks.append(buf)
    return chunks

def parse_markdown(path: Path, size: int = 512, overlap: int = 64) -> list[dict]:
    """按标题切段，再对超长段按长度切。返回[{doc , headinh , chunk_id , text , chars}]。"""
    lines = path.read_text(encoding="utf-8").splitlines()

    blocks: list[tuple[str, str]] = []      #(heading 路径，正文)
    heading: list[str] = []
    buf: list[str] = []
    in_code = False

    def flush() -> None:
        nonlocal buf
        body = "\n".join(buf).strip()
        if body:
            blocks.append(("> ".join(heading) or "(无标题)", body))
        buf = []

    for line in lines:
        if line.strip().startswith("```"):       #代码块内不识别标题
            in_code = not in_code
            buf.append(line)
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m and not in_code:
            flush()
            level = len(m.group(1))
            heading = heading[: level - 1] + [m.group(2).strip()]
            continue
        buf.append(line)
    flush()

    out: list[dict] = []
    for h, body in blocks:
        for piece in _split_long(body, size, overlap):
            out.append({
                "doc": path.name,
                "heading": h,
                "chunk_id": f"{path.stem}#{len(out):03d}",
                "text": piece,
                "chars": len(piece),
            })
    return out



def load_corpus(size: int = 512, overlap: int =64) -> list[dict]:
    """读取 data/下所以 .md 切成一个扁平块列表。"""
    chunks: list[dict] = []
    for path in sorted(DATA_DIR.glob("*.md")):
        chunks.extend(parse_markdown(path, size=size, overlap=overlap))
    return chunks



if __name__ == "__main__":
    for size in (256, 512, 1024):
        cs = load_corpus(size=size)
        lens = [c["chars"] for c in cs]
        docs = len({c["doc"] for c in cs})
        print(f"size={size:5d} 块数={len(cs):4d}, 文档数={docs} "
              f"平均长度={sum(lens) // len(lens):4d} 最长={max(lens):4d} 最短={min(lens)}")

    print("\n=== 样例块 (size=512) ===")
    for c in load_corpus(512)[:2]:
        print("\n---", c["chunk_id"], "|", c["doc"], "|", c["heading"])
        print(c["text"][:120].replace("\n", " "))
