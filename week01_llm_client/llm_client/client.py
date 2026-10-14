"""LLMClient：带超时、重试、日志、token 统计的 LLM 客户端。

这个文件里，__init__ / __aenter__ / __aexit__ 已经写好，
你只需要实现 chat() 方法（见方法里的 docstring）。
"""

import asyncio
import logging

import httpx

from .config import Settings

log = logging.getLogger(__name__)


class LLMClient:
    """异步 LLM 客户端。推荐用法：

        async with LLMClient(settings) as client:
            text = await client.chat("你好")
            print(client.total_tokens)
    """

    def __init__(self, settings: Settings):
        self.s = settings
        self.total_tokens = 0                 # 累计 token 用量（跨多次调用）
        self._client: "httpx.AsyncClient | None" = None

    # ---------- 已写好：连接池的创建与释放 ----------

    async def __aenter__(self):
        # 一个 AsyncClient 贯穿全程，内部维护连接池。
        # 千万不要每次请求都新建客户端，那样连接池等于白建。
        self._client = httpx.AsyncClient(
            base_url=self.s.base_url,
            headers={"Authorization": f"Bearer {self.s.api_key}"},
            timeout=httpx.Timeout(
                connect=10.0,            # 建连超时
                read=self.s.timeout,     # 等响应超时（LLM 慢，这个最重要）
                write=30.0,              # 发请求体超时
                pool=10.0,               # 等空闲连接超时
            ),
        )
        log.debug("HTTP 客户端已创建：base_url=%s", self.s.base_url)
        return self

    async def __aexit__(self, *exc_info):
        await self._client.aclose()
        log.debug("HTTP 客户端已关闭，累计 tokens=%d", self.total_tokens)

    # ---------- 你要实现的部分 ----------

    async def chat(self, prompt, temperature=None, thinking=True,
                   reasoning_effort=None, retries=3):
        #------组装-----
        payload = {
                "model":self.s.model,
                "messages":[{"role":"user","content":prompt}],
                "thinking":{"type":"enabled" if thinking else "disabled"},
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if reasoning_effort is not None:
            payload["reasoning_effort"] = reasoning_effort

        #-----重试循环-----
        for attempt in range(1,retries+1):
            try:
                #-----发送请求-----
                r = await self._client.post("/chat/completions",json=payload)
                r.raise_for_status()
                data = r.json()
                # ---- 响应结构（只列我们关心的字段，完整版见 DeepSeek 官方文档）----
                        # data = {
                        #   "id": "chatcmpl-xxx",
                        #   "model": "deepseek-flash",
                        #   "choices": [
                        #     {
                        #       "index": 0,
                        #       "finish_reason": "stop",        # stop / length / tool_calls / content_filter ...
                        #       "message": {
                        #         "role": "assistant",
                        #         "content": "...",             # ← 答案正文，第 8 步要返回的就是它
                        #         "reasoning_content": "...",   # 思考过程（仅思考模式有）
                        #         "tool_calls": [...]           # 工具调用（第 3 周才用）
                        #       }
                        #     }
                        #   ],
                        #   "usage": {
                        #     "prompt_tokens": 20,
                        #     "completion_tokens": 150,
                        #     "total_tokens": 170,              # ← 第 3 步累加的就是它
                        #     "prompt_cache_hit_tokens": 0,
                        #     "prompt_cache_miss_tokens": 20,
                        #     "completion_tokens_details": {    # ⚠️ 仅思考模式有，所以要 .get 兜底
                        #       "reasoning_tokens": 90
                        #     }
                        #   }
                        # }
                        # 官方文档：https://api-docs.deepseek.com/api/create-chat-completion
                

                #-----统计token-----
                u = data["usage"]
                self.total_tokens += u["total_tokens"]
                reasoning_tokens = (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)
                
                #-----打印日志------
                log.info(
                       "调用成功 | model=%s | tokens:total=%d (prompt=%d, completion=%d, 思考=%d) | 累计=%d",
                        data["model"],u["total_tokens"],u["prompt_tokens"],u["completion_tokens"],reasoning_tokens,self.total_tokens,
                    )
               
                #-----返回-----
                return data["choices"][0]["message"]["content"]
           
            #-----两类异常-----
            except httpx.HTTPStatusError as e:
                code = e.response.status_code
                if code != 429 and code < 500:
                    log.error("客户端错误%s,不重试：%s",code,e.response.text[:200])
                    raise
                log.warning("服务端错误%s,准备重试",code)

            except(httpx.ConnectError,httpx.TimeoutException) as e:
                log.warning("网络问题%s,准备重试",type(e).__name__)

            #-----重试次数用尽-----
            if attempt == retries:
                raise RuntimeError(f"重试{retries}次仍失败")

            #-----退避-----
            await asyncio.sleep(0.5*2**(attempt - 1))