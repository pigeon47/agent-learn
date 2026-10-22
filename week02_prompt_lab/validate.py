"""第 2 周 · 离线自检（不联网、不花 token）。

学什么：
  在花钱跑 API 之前，先确认"数据、schema、提示词"三者本身没问题。
  实验出错时，先跑这个脚本——能排掉一半"其实是数据写错了"的情况。

它检查什么：
  1. schemas/paper_summary.json 是不是一份合法的 JSON Schema
  2. data/samples.jsonl 每行是不是合法 JSON，expected 字段类型对不对
  3. 样本自洽性：摘要里出现了 4 位年份，expected.year 却是 null（或反过来）→ 告警
  4. prompts/*.txt 里有没有留 {abstract} 占位符（没有的话模型拿不到输入）

怎么算过关：输出「全部通过」。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
YEAR_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")

problems: list[str] = []
warnings: list[str] = []


def check_schema() -> dict:
    path = BASE_DIR / "schemas" / "paper_summary.json"
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        problems.append(f"schema 不是合法 JSON：{exc}")
        return {}

    try:
        import jsonschema
    except ImportError:
        problems.append("没装 jsonschema：E:\\agent-learn\\env\\python.exe -m pip install jsonschema")
        return schema

    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        print(f"[OK] schema 合法：{len(schema.get('properties', {}))} 个字段")
    except Exception as exc:
        problems.append(f"schema 结构非法：{exc}")
    return schema


def check_samples(schema: dict) -> list[dict]:
    path = BASE_DIR / "data" / "samples.jsonl"
    samples, seen = [], set()
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            problems.append(f"samples.jsonl 第 {lineno} 行不是合法 JSON：{exc}")
            continue

        sid = item.get("id")
        if not sid:
            problems.append(f"第 {lineno} 行缺 id")
        elif sid in seen:
            problems.append(f"id 重复：{sid}")
        seen.add(sid)

        if not item.get("abstract"):
            problems.append(f"{sid}: abstract 为空")

        exp = item.get("expected") or {}
        year, n_authors = exp.get("year"), exp.get("n_authors")
        if not (year is None or isinstance(year, int)):
            problems.append(f"{sid}: expected.year 必须是整数或 null，现在是 {year!r}")
        if not (isinstance(n_authors, int) and n_authors >= 1):
            problems.append(f"{sid}: expected.n_authors 必须是 ≥1 的整数")

        # 自洽性：摘要里有年份 ↔ expected.year 不是 null
        found = YEAR_RE.search(item.get("abstract", ""))
        if found and year is None:
            warnings.append(f"{sid}: 摘要里出现 {found.group(0)}，但 expected.year 是 null（是不是漏标了？）")
        if not found and year is not None:
            warnings.append(f"{sid}: 摘要里没有 4 位年份，但 expected.year={year}（确认一下）")

        samples.append(item)

    print(f"[OK] 样本 {len(samples)} 条，id 无重复")
    return samples


def check_prompts() -> None:
    for name in ("zero", "few", "cot"):
        path = BASE_DIR / "prompts" / f"{name}.txt"
        if not path.exists():
            problems.append(f"缺提示词文件：{path.name}")
            continue
        text = path.read_text(encoding="utf-8")
        if "{abstract}" not in text:
            problems.append(f"prompts/{name}.txt 没有 {{abstract}} 占位符，模型拿不到摘要")
        if "json" not in text.lower():
            warnings.append(f"prompts/{name}.txt 里没出现 json 字样（response_format 之外，提示词也要求明说）")
    print("[OK] 三份提示词都在，且都有 {abstract} 占位符")


def main() -> None:
    schema = check_schema()
    check_samples(schema)
    check_prompts()

    print()
    for w in warnings:
        print(f"[告警] {w}")
    for p in problems:
        print(f"[错误] {p}")

    if problems:
        sys.exit(f"\n未通过：{len(problems)} 个错误，{len(warnings)} 个告警")
    print(f"\n全部通过（{len(warnings)} 个告警，不影响运行）")


if __name__ == "__main__":
    main()
