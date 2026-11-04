"""工具公共设施：路径白名单、临时目录、UA、HTML 转文本。"""
from __future__ import annotations

import re
from pathlib import Path

ALLOWED_ROOT = Path(__file__).resolve().parents[3]
SCRATCH = ALLOWED_ROOT / "scratch"
SCRATCH.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")
ACCEPT = "zh-CN,zh;q=0.9,en;q=0.8"

_TAG = re.compile(r"(?s)<[^>]+>")
_SCRIPT = re.compile(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>")



def html_to_text(html: str) -> str:
    html = _SCRIPT.sub(" ",html)
    html = _TAG.sub(" ",html)
    html = (html.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">")
                .replace("&quot;", '"').replace("&#39;", "'"))
    return re.sub(r"\s+", " ", html).strip()



def safe_path(path: str, must_exist: bool = True) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = ALLOWED_ROOT / p
    p = p.resolve()
    if not str(p).startswith(str(ALLOWED_ROOT)):
        raise ValueError(f"只能访问 {ALLOWED_ROOT} 以内的路径")
    if must_exist and not p.exists():
        raise ValueError(f"不存在: {path}")
    return p



def scratch_path(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = ALLOWED_ROOT / p
    p = p.resolve()
    if not str(p).startswith(str(SCRATCH)):
        raise ValueError(f"只允许写到 {SCRATCH} 以内")
    return p


# ------------------------------------------------------------------ 敏感文件
# 即使在 ALLOWED_ROOT 以内，这些文件也不允许读写（凭据类）
_SENSITIVE_NAMES = {
    ".env", ".env.local", ".env.development", ".env.production",
    "id_rsa", "id_ed25519", "id_dsa", "known_hosts",
    ".netrc", ".pgpass", "credentials",
}
_SENSITIVE_SUFFIX = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore", ".crt"}
_SENSITIVE_PARTS = {".git", ".ssh", ".aws", ".gnupg", ".kube"}


def is_sensitive(p: Path) -> bool:
    """判断是不是凭据类文件：白名单只保证"路径合法"，这里负责"文件可读"。"""
    name = p.name.lower()
    if name in _SENSITIVE_NAMES or name.startswith(".env"):
        return True
    if p.suffix.lower() in _SENSITIVE_SUFFIX:
        return True
    parts = {part.lower() for part in p.parts}
    return bool(parts & _SENSITIVE_PARTS)
