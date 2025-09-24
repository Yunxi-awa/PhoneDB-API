import asyncio
from functools import wraps

import aiohttp
from loguru import logger

from .response import PhoneDBResponse
def async_retry(max_attempts=3, initial_wait=1, max_wait=10):
    """
    异步重试装饰器

    Args:
        max_attempts: 最大重试次数
        initial_wait: 初始等待时间（秒）
        max_wait: 最大等待时间（秒）
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retry_count = 0
            last_exception = None

            while retry_count < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except (aiohttp.ClientError,
                        asyncio.TimeoutError,
                        ConnectionError,
                        OSError) as e:
                    last_exception = e
                    retry_count += 1

                    if retry_count >= max_attempts:
                        break

                    # 指数退避策略
                    wait_time = min(initial_wait * (2 ** (retry_count - 1)), max_wait)
                    await asyncio.sleep(wait_time)

            # 如果所有重试都失败了，抛出最后一个异常
            raise last_exception or Exception("Unknown error occurred during retry")

        return wrapper

    return decorator

class Client(aiohttp.ClientSession):
    def __init__(self, *args, **kwargs):
        """
        初始化 Client 类的实例。

        Args:
            *args: 位置参数，传递给父类的初始化方法。
            **kwargs: 关键字参数，传递给父类的初始化方法。
        """
        kwargs.pop("response_class", None)
        super().__init__(*args, **kwargs, response_class=PhoneDBResponse)

    @async_retry(max_attempts=3, initial_wait=1, max_wait=10)
    async def retryable_get(self, url, **kwargs) -> PhoneDBResponse:
        """可重试的GET请求"""
        logger.debug(f"GET {url}")
        return await self.get(url, **kwargs)

    @async_retry(max_attempts=3, initial_wait=1, max_wait=10)
    async def retryable_post(self, url, **kwargs) -> PhoneDBResponse:
        """可重试的POST请求"""
        logger.debug(f"POST {url}")
        return await self.post(url, **kwargs)
