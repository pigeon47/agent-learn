"""配置管理：所有"环境相关"的东西都从这里拿。

设计三原则：
  1. 集中：别让 api_key、base_url 散落在各个文件里
  2. 快速失败：缺配置立刻报错，并告诉对方怎么修（而不是跑到一半报 401）
  3. 脱敏：打印配置时永远只显示密钥的头尾
"""

import os

try:
    # 装了 python-dotenv 就从 .env 读；没装则退化成读系统环境变量
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:                      # pragma: no cover
    pass


class Settings:
    """从环境变量读取配置。用法：settings = Settings()"""

    def __init__(self):
        self.api_key = os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.environ.get("DEEPSEEK_MODEL", "deepseek-flash")
        self.timeout = float(os.environ.get("DEEPSEEK_TIMEOUT", "60"))

        # ---- 快速失败：缺 Key 时不要沉默地继续 ----
        # 报错信息里要写清"错在哪"和"怎么修"，这样半夜看日志也能自己搞定
        if not self.api_key:
            raise RuntimeError(
                "缺少环境变量 DEEPSEEK_API_KEY。\n"
                "  修法：在项目根目录执行 Copy-Item .env.example .env，"
                "然后用记事本打开 .env，把 sk-在这里填你的密钥 换成真实 Key。\n"
                "  注意：.env 不要提交到 Git。"
            )

        # 顺手挡掉一个常见错误：把 Key 连引号一起复制进去
        if self.api_key.startswith(("'", '"')) or self.api_key.endswith(("'", '"')):
            raise RuntimeError(
                f"DEEPSEEK_API_KEY 的首尾带引号，说明复制时把引号也带上了："
                f"{self.api_key[:8]}...\n  .env 里不要写引号，直接写 sk-xxx 即可。"
            )

    def __repr__(self):
        """打印配置时只显示密钥头尾，避免日志/截图泄露完整 Key。"""
        if self.api_key:
            masked = f"{self.api_key[:6]}...{self.api_key[-4:]}"
        else:
            masked = "None"
        return (f"Settings(base_url={self.base_url}, model={self.model}, "
                f"timeout={self.timeout}, api_key={masked})")
