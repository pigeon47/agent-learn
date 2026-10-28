r"""长期记忆库：用 sqlite3 存 ⌈偏好与事实⌋ 键值对，支持按会话隔离与关键词检索。

为什么用 sqlite3：
    标准库自带、零依赖、单文件、支持 SQL 查询并发读写;
    记忆量在几千条以内完全够用，不需要向量库。
"""
from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "memory.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session    TEXT NOT NULL,
    key        TEXT NOT NULL,
    value      TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    hits       INTEGER NOT NULL DEFAULT 0,
    UNIQUE(session, key)
);
CREATE INDEX IF NOT EXISTS idx_facts_session ON facts(session);
"""

_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]+|\d+(?:\.\d+)?|[\u4e00-\u9fff]+")



def tokenize(text: str) -> set[str]:
    """中文取单字 + 双字，英文数字按词。用于关键词匹配。"""
    tokens: set[str] = set()
    for m in _WORD.finditer(text):
        s = m.group()
        if "\u4e00" <= s[0] <= "\u9fff":
            tokens.update(s)
            tokens.update(s[i : i+2] for i in range(len(s) - 1))
        else:
            tokens.add(s.lower())
    return tokens



class Memory:
    def __init__ (self, session: str = "default", db_path: Path | str = DB_PATH) -> None:
        self.session = session
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---------------------------------------------------------------- 写入
    def upsert(self, key: str, value: str) -> None:
        """同 session 下同 key 覆盖, 不同 key 新增。"""
        now = time.time()
        self.conn.execute(
            """INSERT INTO facts (session, key, value, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(session, key) DO UPDATE SET
                   value = excluded.value,
                   updated_at = excluded.updated_at""",
            (self.session, key, value, now, now),
        )
        self.conn.commit()

    def forget(self, key: str | None = None) -> int:
        if key is None:
            cur = self.conn.execute("DELETE FROM facts WHERE session = ?", (self.session,))
        else:
            cur = self.conn.execute(
                "DELETE FROM facts WHERE session = ? AND key = ?", (self.session, key))
        self.conn.commit()
        return cur.rowcount

    # ---------------------------------------------------------------- 读取
    def get(self, key: str) -> str | None:
        row = self.conn.execute(
            "SELECT value FROM facts WHERE session = ? AND key = ?",
            (self.session, key)).fetchone()
        return row["value"] if row else None

    def all(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, key, value, updated_at, hits FROM facts "
            "WHERE session = ? ORDER BY updated_at DESC", (self.session,)).fetchall()
        return [dict(r) for r in rows]
    
    def search(self, query: str, limit: int = 5) -> list[dict]:
        """按关键词重合度打分，返回最相关的几条记忆。"""
        q_tokens = tokenize(query)
        if not q_tokens:
            return []
        scored = []
        for row in self.all():
            text = f"{row['key']} {row['value']}"
            overlap = len(q_tokens & tokenize(text))
            if overlap:
                scored.append((overlap, row))
        scored.sort(key=lambda x: (-x[0], -x[1]["updated_at"]))
        return [row for _, row in scored[:limit]]

    def touch(self, ids: list[int]) -> None:
        """记录命中次数 (以后可用于淘汰长期不用的记忆)。"""
        if not ids:
            return
        self.conn.executemany("UPDATE facts SET hits = hits + 1 WHERE id = ?",
                              [(i,) for i in ids])
        self.conn.commit()

    # ---------------------------------------------------------------- 渲染
    def as_prompt(self, query: str, limit: int = 5, max_inline: int = 20) -> str:
        """渲染成提示词片段。

        记忆条数 ≤ max_inline 时全量注入（召回率 100%，几百 token 可接受）；
        超过时才退回关键词检索（避免上下文爆炸）。
        """
        all_rows = self.all()
        if not all_rows:
            return ""
        if len(all_rows) <= max_inline or not query:
            rows = all_rows[:max_inline]
        else:
            rows = self.search(query, limit)
        if not rows:
            return ""
        lines = [f"- {r['key']}：{r['value']}" for r in rows]
        self.touch([r["id"] for r in rows])
        return "关于当前用户的已知信息：\n" + "\n".join(lines)

    def close(self) -> None:
        self.conn.close()

if __name__ == "__main__":
    m = Memory(session="demo")
    m.forget()
    m.upsert("name", "张伟")
    m.upsert("learning_goal", "12 周内做出可部署的 AI Agent")
    m.upsert("preference_style", "回答要简洁，不要用表情符号")
    m.upsert("name", "张伟 (更新过)")           # 同 key 覆盖

    print("=== 全部记忆 ===")
    for r in m.all():
        print(f" {r['key']:18s} = {r['value']}")


    print("\n=== 检索：'我叫什么名字' ===")
    for r in m.search("我叫什么名字"):
        print(f" {r['key']:18s} = {r['value']}")


    print("\n=== 渲染成提示词片段 ===")
    print(m.as_prompt("我的学习目标是什么"))


    print("\n=== 会话隔离 ===")
    m2 = Memory(session="other")
    print(" 另一个 session 看到：", m2.all())
    m.close()
    m2.close()