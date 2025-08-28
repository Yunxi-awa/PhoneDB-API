import asyncio
from abc import ABC, abstractmethod

import curl_cffi
from loguru import logger

from .config import SessionConfig
from .exception import ResponseError


class WebSession(ABC):
    """
    基础WebSession类
    """

    @abstractmethod
    async def get(self, url):
        """

        :param url:
        """
        raise NotImplementedError("WebSession.get()方法未实现.")

    @abstractmethod
    async def close(self):
        """
        关闭会话
        :return:
        """
        raise NotImplementedError("WebSession.close()方法未实现.")

    @abstractmethod
    def set_max_workers(self, max_workers: int):
        """
        设置会话并发数
        :return:
        """
        raise NotImplementedError("WebSession.set_max_workers()方法未实现.")


class WebSessionCurlCffi(curl_cffi.AsyncSession, WebSession):
    """
    增强的异步会话类, 拥有更强大的反爬功能
    """

    def __init__(self, session_config: SessionConfig = None):
        super().__init__(**session_config.kwargs)
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

    def set_max_workers(self, max_workers: int):
        self.max_clients = max_workers
        self.init_pool()
