import asyncio

import curl_cffi
from loguru import logger

from .config import SessionConfig
from .exception import ResponseError


class EnhancedAsyncSession(curl_cffi.AsyncSession):
    def __init__(self, session_config: SessionConfig = None):
        super().__init__(**(session_config.kwargs if session_config is not None else {}))
        self._session_config = session_config if session_config is not None else SessionConfig()

    async def request(self, method: curl_cffi.requests.HttpMethod, url: str, **kwargs):
        for i in range(1, self._session_config.max_retries + 1):
            try:
                response: curl_cffi.Response = await super().request(method, url, **kwargs)
                return response
            except curl_cffi.CurlError as e:
                logger.error(f"请求({url})失败第({i})次, 错误信息[{e}]")
                if i == self._session_config.max_retries:
                    raise ResponseError(f"请求({url})完全失败, 错误信息[{e}]")
                await asyncio.sleep(self._session_config.delay_ms / 1000)
        return None
