"""第 2 周 · 必做 1 & 2 的运行器。

学什么（读完这一页就够动手了）：
  1. 结构化输出 = 接口层保证（response_format） + 提示词保证（写明字段），两者缺一不可。
  2. 校验不能靠肉眼：json.loads 只证明"是 JSON"，jsonschema 才证明"字段对不对"。
  3. 对比实验要记录**成功率和成本**两件事：token 用接口返回的 usage，别自己估。

动手改哪：
  - 想加维度（比如换 temperature、换模型）：改 build_payload() 和下面的命令行参数。
  - 想改判定标准：改 judge()。
  - 提示词不要写在这里，去改 prompts/*.txt。

怎么算过关：
  python runner.py --prompt all --limit 20
  → results/ 下生成 three 份 csv，且 zero 的成功率 ≥ 95%
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROMPT_FILES = {
    "zero": BASE_DIR / "prompts" / "zero.txt",
    "few": BASE_DIR / "prompts" / "few.txt",
    "cot": BASE_DIR / "prompts" / "cot.txt",
}


# ---------------------------------------------------------------- 配置与依赖
def load_env() -> None:
    """先找本目录 .env，再退回 week01 的那份；都没有就依赖系统环境变量。"""
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("[警告] 没装 python-dotenv，只能读系统环境变量", file=sys.stderr)
        return

    candidates = [BASE_DIR / ".env", BASE_DIR.parent / "week01_llm_client" / ".env"]
    for path in candidates:
        if path.exists():
            load_dotenv(path)
            print(f"[配置] 读取 {path}")
            return
    load_dotenv()


def need_package(name: str, hint: str):
    try:
        return __import__(name)
    except ImportError:
        sys.exit(f"[缺少依赖] {name}\n  安装：{hint}")


def settings() -> dict:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        sys.exit(
            "缺少 DEEPSEEK_API_KEY。\n"
            "  修法：把 week01_llm_client/.env 复制到本目录，或设置系统环境变量。"
        )
    return {
        "api_key": key,
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-flash"),
        "timeout": float(os.environ.get("DEEPSEEK_TIMEOUT", "90")),
    }


# ---------------------------------------------------------------- 调用
def build_payload(cfg: dict, prompt: str, temperature: float, thinking: bool) -> dict:
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": "你只输出一个 JSON 对象，不输出任何额外文字。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        # 关键：接口层保证返回合法 JSON（但提示词里仍然必须写明字段，见 prompts/*.txt）
        "response_format": {"type": "json_object"},
        "stream": False,
    }
    # 思考模式下 temperature 无效，做对比实验时必须关掉思考
    if not thinking:
        payload["thinking"] = {"type": "disabled"}
    return payload


def chat_json(httpx, cfg: dict, prompt: str, temperature: float, thinking: bool) -> tuple[str, dict, int]:
    started = time.perf_counter()
    with httpx.Client(timeout=cfg["timeout"]) as client:
        resp = client.post(
            f"{cfg['base_url']}/chat/completions",
            headers={
                "Authorization": f"Bearer {cfg['api_key']}",
                "Content-Type": "application/json",
            },
            json=build_payload(cfg, prompt, temperature, thinking),
        )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {}) or {}
    return content, usage, elapsed_ms


# ---------------------------------------------------------------- 判定
def judge(obj: dict, expected: dict, validator) -> tuple[bool, bool, bool, str]:
    """返回 (schema_ok, year_ok, authors_ok, 错误信息)。"""
    errors = sorted(validator.iter_errors(obj), key=lambda e: str(e.path))
    schema_ok = not errors
    err_msg = f"schema: {errors[0].message}" if errors else ""
    
    got_year = obj.get("year")
    if isinstance(got_year, str) and got_year.strip().isdigit():
        got_year = int(got_year.strip())
    year_ok = got_year == expected.get("year")

    got_authors = obj.get("authors")
    authors_ok = isinstance(got_authors, list) and len(got_authors) == expected.get("n_authors")
    return schema_ok, year_ok, authors_ok, err_msg


# ---------------------------------------------------------------- 主流程
def run_one(httpx, cfg, kind, samples, validator, template, limit, temperature, thinking, out_dir):
    rows = []
    total_ms = 0
    for sample in samples[:limit]:
        prompt = template.replace("{abstract}", sample["abstract"])
        row = {
            "id": sample["id"],
            "ok": 0,
            "year_ok": 0,
            "authors_ok": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": 0,
            "error": "",
            "title": "",
            "content":"",     #多存一组原始输出，方便失败样本复盘，表头由这些键生成
        }
        try:
            content, usage, ms = chat_json(httpx, cfg, prompt, temperature, thinking)
            row["content"] = content[:800]   #输入限制字数为800让.csv文件大小不要太大并且不会很难读，读入依旧是json.loads()依旧使用原文
            row["prompt_tokens"] = usage.get("prompt_tokens", 0)
            row["completion_tokens"] = usage.get("completion_tokens", 0)
            row["latency_ms"] = ms
            total_ms += ms
            obj = json.loads(content)                     # 1) 是不是 JSON
            ok, year_ok, authors_ok, err = judge(obj, sample["expected"], validator)
            row.update(ok=int(ok), year_ok=int(year_ok), authors_ok=int(authors_ok),
                       error=err, title=str(obj.get("title", ""))[:60])
        except json.JSONDecodeError as exc:
            row["error"] = f"JSON 解析失败: {exc}"
        except Exception as exc:                          # 网络/HTTP/字段缺失
            row["error"] = str(exc)[:200]
        rows.append(row)
        flag = "OK " if row["ok"] else "ERR"
        print(f"  [{flag}] {row['id']}  year={row['year_ok']} authors={row['authors_ok']} "
              f"tok={row['prompt_tokens']}+{row['completion_tokens']} {row['latency_ms']}ms"
              + (f"  {row['error'][:60]}" if row["error"] else ""))

    n = len(rows)
    out = out_dir / f"{kind}.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["id"])
        writer.writeheader()
        writer.writerows(rows)

    def rate(key):
        return sum(r[key] for r in rows) / n if n else 0.0

    avg = lambda key: (sum(r[key] for r in rows) / n if n else 0)
    summary = {
        "prompt": kind,
        "n": n,
        "success_rate": round(rate("ok") * 100, 1),
        "year_hit": round(rate("year_ok") * 100, 1),
        "authors_hit": round(rate("authors_ok") * 100, 1),
        "avg_prompt_tokens": round(avg("prompt_tokens")),
        "avg_completion_tokens": round(avg("completion_tokens")),
        "avg_latency_ms": round(avg("latency_ms")),
        "csv": str(out),
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="论文摘要 → JSON：zero / few / cot 对比")
    parser.add_argument("--prompt", default="zero", choices=["zero", "few", "cot", "all"])
    parser.add_argument("--limit", type=int, default=20, help="跑多少条样本")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--thinking", action="store_true",
                        help="开启思考模式（会让 temperature 失效，做对比实验别开）")
    parser.add_argument("--out-dir", default=str(BASE_DIR / "results"))
    args = parser.parse_args()

    load_env()
    httpx = need_package("httpx", "E:\\agent-learn\\env\\python.exe -m pip install httpx")
    jsonschema = need_package("jsonschema", "E:\\agent-learn\\env\\python.exe -m pip install jsonschema")

    schema = json.loads((BASE_DIR / "schemas" / "paper_summary.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    samples = [json.loads(line) for line in
               (BASE_DIR / "data" / "samples.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

    cfg = settings()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    kinds = ["zero", "few", "cot"] if args.prompt == "all" else [args.prompt]
    summaries = []
    for kind in kinds:
        template = PROMPT_FILES[kind].read_text(encoding="utf-8")
        print(f"\n=== {kind}（{min(args.limit, len(samples))} 条） ===")
        summaries.append(run_one(httpx, cfg, kind, samples, validator, template,
                                 args.limit, args.temperature, args.thinking, out_dir))

    print("\n=== 汇总（复制进 README 的对比表） ===")
    header = ["prompt", "n", "success_rate", "year_hit", "authors_hit",
              "avg_prompt_tokens", "avg_completion_tokens", "avg_latency_ms"]
    print(" | ".join(header))
    for s in summaries:
        print(" | ".join(str(s[h]) for h in header))
    summaries_path = out_dir / "summary.json"
    old = []
    if summaries_path.exists():
        try:
            old = json.loads(summaries_path.read_text(encoding="utf-8"))
            if not isinstance(old, list):
                old = [old];
        except(json.JSONDecodeError, OSError):
            old = []

    replaced = {s["prompt"]for s in summaries}
    merged = [r for r in old if r.get("prompt") not in replaced]
    merged.extend(summaries)

    summaries_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )

if __name__ == "__main__":
    main()
