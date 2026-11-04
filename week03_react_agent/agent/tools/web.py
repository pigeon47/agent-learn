"""联网工具：搜索 + 抓网页。"""
from __future__ import annotations

import re
from urllib.parse import urljoin

import httpx

from .base import ACCEPT, UA ,html_to_text

_H3 = re.compile(r"(?s)<h3[^>]*>.*?</h3>")
_A = re.compile(r'(?s)<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>')
_JS_REDIRECT = re.compile(r'window\.location\.replace\("([^"]+)"\)')
_BING_ITEM = re.compile(r'(?s)<li class="b_algo".*?</li>')
_BING_LINK = re.compile(r'(?s)<h2>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>')



def _resolve_redirect(url: str) -> str:
    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True,
                         headers={"User-Agent": UA, "Accept-Language": ACCEPT})
        if str(resp.url) != url:
            return str(resp.url)
        m = _JS_REDIRECT.search(resp.text)
        if m:
            return m.group(1)
    except Exception:
        pass
    return url



def _search_sogou(query: str, max_results: int, resolve: bool) -> list[dict]:
    resp = httpx.get("https://www.sogou.com/web", params={"query": query},
                     timeout=15, follow_redirects=True,
                     headers={"User-Agent": UA, "Accept-Language": ACCEPT})
    resp.raise_for_status()
    html = resp.text
    marks = list(_H3.finditer(html))
    results: list[dict] = []
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else min(mark.end() + 1200, len(html))
        block = html[mark.start():end]
        a = _A.search(block)
        if not a:
            continue
        url = urljoin("https://www.sogou.com", a.group(1))
        if resolve:
            url = _resolve_redirect(url)
        results.append({"title": html_to_text(a.group(2))[:80], "url": url,
                        "snippet": html_to_text(block[mark.end() - mark.start():])[:200]})
        if len(results) >= max_results:
            break
    return results



def _search_bing(query: str, max_results: int, resolve: bool) -> list[dict]:
    resp = httpx.get("https://cn.bing.com/search", params={"q": query},
                     timeout=15, follow_redirects=True,
                     headers={"User-Agent": UA, "Accept-Language": ACCEPT})
    resp.raise_for_status()
    results = []
    for block in _BING_ITEM.findall(resp.text)[:max_results]:
        m = _BING_LINK.search(block)
        if m:
            results.append({"title": html_to_text(m.group(2))[:80],
                            "url": m.group(1),
                            "snippet": html_to_text(block)[:200]})
    return results



_ENGINES = {"sogou": _search_sogou, "bing": _search_bing}



def web_search(query: str, max_results: int = 5, engine: str = "sogou",
               resolve_links: bool = True) -> dict:
    order = [engine] + [e for e in ("sogou", "bing") if e != engine]
    errors = []
    for name in order:
        fn = _ENGINES.get(name)
        if fn is None:
            continue
        try:
            results = fn(query, max_results, resolve_links)
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}")
            continue
        if results:
            return {"query": query, "engine": name, "count": len(results), "results": results}
        errors.append(f"{name}：无结果")
    raise RuntimeError("搜索失败 (" + "; ".join(errors) + ")")



def fetch_url(url: str, max_chars: int = 3000) -> dict:
    if not url.startswith(("http://", "https://")):
        raise ValueError("只支持 http/https 链接")
    real = _resolve_redirect(url)
    resp = httpx.get(real, timeout=15, follow_redirects=True,
                     headers={"User-Agent": UA, "Accept-Language": ACCEPT})
    resp.raise_for_status()
    text = html_to_text(resp.text)
    return {"url": str(resp.url), "status": resp.status_code,
            "chars": len(text), "text": text[:max_chars]}



SPECS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "联网搜索。需要最新、具体、可能过时的信息时先调用它，不哟啊凭记忆回答。"
                "返回标题、真实链接、摘要; 摘要不够再用 fetch_url 读原文。"
            ),
            "parameters":{
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "关键词，越具体越好"},
                    "max_results": {"type": "integer", "description": "返回几条，默认 5"},
                    "engine": {"type": "string", "enum": ["sogou", "bing"],
                               "description": "默认 sogou; 需要直连链接或英文内容用 bing"},
                    "resolve_links": {"type": "boolean",
                                      "description": "是否还原跳转链，默认 true"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "抓取网页正文纯文本。搜索摘要不够，需要原文细节时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "完整链接"},
                    "max_chars": {"type": "integer", "descrption": "最多返回字符，默认 3000"},
                },
                "required": ["url"],
            },
        },
    },
]

IMPL = {"web_search": web_search, "fetch_url": fetch_url}
