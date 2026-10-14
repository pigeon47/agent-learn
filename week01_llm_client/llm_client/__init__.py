"""llm_client 包：第 1 周的 LLM 客户端。

__init__.py 的职责只有一个：把包里的东西"提到门口"，让外部可以这样写：

    from llm_client import Settings, LLMClient

而不是：

    from llm_client.config import Settings
    from llm_client.client import LLMClient

注意：这里只做导入，不要写耗时操作（发网络请求、读大文件），
因为别人 import 这个包时，这几行会立刻执行。
"""

from .config import Settings
from .client import LLMClient

__all__ = ["Settings", "LLMClient"]
