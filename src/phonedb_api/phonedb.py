import abc
import asyncio
import math
import urllib.parse
from functools import wraps
from typing import AsyncGenerator, Generator

import aiohttp
import curl_cffi
import lxml.etree
from loguru import logger

from .database import AbstractDatabase
from .instance import InstMeta, InstCat, Instance
from .parse import QueryFormParser, InstanceParser
from .runner import AbstractAsyncRunner


def sync_retry(max_attempts=3, initial_wait=1, max_wait=10):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_count = 0
            last_exception = None

            while retry_count < max_attempts:
                try:
                    return func(*args, **kwargs)
                except (
                        curl_cffi.CurlError,
                        aiohttp.ClientError,
                        ConnectionError,
                        OSError
                ) as e:
                    logger.error(f"Request failed (attempt {retry_count + 1}/{max_attempts}): {e}")
                    last_exception = e
                    retry_count += 1

                    if retry_count >= max_attempts:
                        break

                    # 指数退避策略
                    wait_time = min(initial_wait * (2 ** (retry_count - 1)), max_wait)
                    asyncio.sleep(wait_time)

            # 如果所有重试都失败了，抛出最后一个异常
            raise last_exception or Exception("Unknown error occurred during retry")

        return wrapper

    return decorator


# Solana saga
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
                except (
                        curl_cffi.CurlError,
                        aiohttp.ClientError,
                        asyncio.TimeoutError,
                        ConnectionError,
                        OSError
                ) as e:
                    logger.error(f"Request failed (attempt {retry_count + 1}/{max_attempts}): {e}")
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


class AbstractPhoneDBSession(abc.ABC):
    @abc.abstractmethod
    def get_latest_id(self, inst_cat: InstCat) -> int:
        """
        获取最新实例ID
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_data(self, inst_meta: InstMeta) -> Instance:
        """
        获取实例数据
        """
        raise NotImplementedError

    @abc.abstractmethod
    def search_website(self, query: str, inst_cat: InstCat) -> Generator[InstMeta]:
        """
        搜索实例
        """
        raise NotImplementedError

    @abc.abstractmethod
    def search_database(self, query: str, inst_cat: InstCat) -> Generator[Instance]:
        """
        搜索实例
        """
        raise NotImplementedError

    @abc.abstractmethod
    def query_website(self, **kwargs) -> list[InstMeta]:
        """
        查询实例
        """
        raise NotImplementedError

    @abc.abstractmethod
    def query_database(self, **kwargs) -> list[Instance]:
        """
        查询实例
        """
        raise NotImplementedError


class PhoneDBHTTPSession(AbstractPhoneDBSession):
    BASE_URL = "https://phonedb.net/"

    def __init__(
            self,
            runner: AbstractAsyncRunner,
            database: AbstractDatabase,
            **kwargs
    ):
        self.runner = runner
        self.database = database

        self.curl_cffi_session = curl_cffi.AsyncSession(**kwargs)
        self.aiohttp_session = aiohttp.ClientSession()

    async def __aenter__(self):
        await self.database.load()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.curl_cffi_session.close()
        await self.aiohttp_session.close()
        await self.database.dump()

    @async_retry(max_attempts=8, initial_wait=1, max_wait=10)
    async def get_latest_id(self, inst_cat: InstCat) -> int:
        response = await self.curl_cffi_session.get(
            "https://phonedb.net/index.php",
            params={
                "m": inst_cat,
                "s": "list"
            }
        )

        tree = lxml.etree.HTML(response.text)
        href = tree.xpath("/html/body/div[5]/div[1]/div[1]/a")[0].get("href")
        parsed_url = urllib.parse.urlparse(href)
        query = urllib.parse.parse_qs(parsed_url.query)
        return int(query["id"][0])

    @async_retry(max_attempts=8, initial_wait=1, max_wait=10)
    async def get_data(self, inst_meta: InstMeta) -> Instance:
        if inst_meta not in self.database:
            # logger.debug(f"No {inst_meta}")
            response = await self.curl_cffi_session.get(
                f"https://phonedb.net/index.php",
                params={
                    "m": inst_meta.inst_cat,
                    "id": inst_meta.inst_id,
                    "d": "detailed_specs"
                }
            )
            self.database.add_data(inst_meta, (await InstanceParser(inst_meta, response.text).parse()).data)
        return Instance(inst_meta, self.database.get_data(inst_meta))

    async def get_data_multi(self, inst_metas: list[InstMeta]) -> AsyncGenerator[Instance]:
        for inst_meta in inst_metas:
            self.runner.register(
                self.get_data(inst_meta)
            )
        logger.debug(f"Register {len(inst_metas)} tasks.")
        count = 0
        async for data in self.runner.run():
            yield data
            count += 1
            logger.debug(f"Progress: {count}/{len(inst_metas)}")

    @sync_retry(max_attempts=8, initial_wait=1, max_wait=10)
    async def search_website(self, query: str, inst_cat: InstCat) -> AsyncGenerator[InstMeta]:
        # 为初始请求添加重试
        response = await self.curl_cffi_session.post(
            f"https://phonedb.net/index.php",
            params={
                "m": inst_cat,
                "s": "list"
            },
            data={
                "search_exp": query,
                "search_header": "",
            }
        )

        tree = lxml.etree.HTML(response.text)
        results_count = int(tree.xpath("/html/body/div[4]/text()[1]")[0].split(" ")[0])

        # Do-While
        for i in range(1, math.ceil(results_count / 29)):
            filter_arg = i * 29
            # 为分页请求添加重试
            self.runner.register(self.curl_cffi_session.post(
                f"https://phonedb.net/index.php",
                params={
                    "m": inst_cat,
                    "s": "list",
                    "filter": filter_arg
                },
                data={
                    "search_exp": query,
                    "search_header": "",
                }
            ))


        async for response in self.runner.run():
            tree = lxml.etree.HTML(response.text)
            for j in tree.xpath("/html/body/div[5]")[0].getchildren():
                if j.tag != "div" or j.get("style"):
                    continue
                yield InstMeta(
                    inst_cat=inst_cat,
                    inst_id=int(urllib.parse.parse_qs(
                        urllib.parse.urlparse(j.getchildren()[0].getchildren()[0].get("href")).query
                    )["id"][0])
                )

    async def search_database(self, query: str, inst_cat: InstCat) -> AsyncGenerator[Instance]:
        for inst_id, data in self.database.search_data(inst_cat, query):
            yield Instance(InstMeta(inst_cat, inst_id), data)

    @sync_retry(max_attempts=8, initial_wait=1, max_wait=10)
    async def query_website(self, inst_cat: InstCat, params: dict) -> AsyncGenerator[InstMeta]:
        # 为初始请求添加重试
        response = await self.curl_cffi_session.get(
            f"https://phonedb.net/index.php",
            params={
                "m": inst_cat,
                "s": "query",
                "d": "detailed_specs"
            }
        )

        payload = await QueryFormParser(response.text).parse(params)
        # 为POST请求添加重试
        response = await self.aiohttp_session.post(
            f"https://phonedb.net/index.php",
            params={
                "m": inst_cat,
                "s": "query",
                "d": "detailed_specs"
            },
            data=payload
        )

        tree = lxml.etree.HTML(await response.text())
        text = tree.xpath("/html/body/div[5]/form/div[2]/text()[1]")[0]
        if "no content" in text.lower():
            return
        results_count = int(text.split(" ")[0])

        for i in range(1, math.ceil(results_count / 29)):
            filter_arg = i * 29
            # 为分页请求添加重试
            self.runner.register(self.aiohttp_session.post(
                f"https://phonedb.net/index.php",
                params={
                    "m": inst_cat,
                    "s": "query",
                    "d": "detailed_specs"
                },
                data=payload | dict(result_lower_limit=str(filter_arg))
            ))


        async for response in self.runner.run():
            tree = lxml.etree.HTML(await response.text())
            for div in tree.xpath("/html/body/div[5]/form")[0].getchildren():
                if (
                        div.tag != "div"
                        or div.get("style")
                        or div.get("class") != "content_block"
                        or div.getchildren()[0].get("class") != "content_block_title"
                ):
                    continue
                yield InstMeta(
                    inst_cat=inst_cat,
                    inst_id=int(urllib.parse.parse_qs(
                        urllib.parse.urlparse(div.getchildren()[0].getchildren()[0].get("href")).query
                    )["id"][0])
                )

    async def query_database(self, inst_cat: InstCat, params: dict) -> AsyncGenerator[Instance]:
        for instance in self.database.query_data(inst_cat, params):
            yield instance
