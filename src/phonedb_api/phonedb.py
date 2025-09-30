import abc
import math
import urllib.parse
from typing import AsyncGenerator

import lxml.etree

from .client import Client
from .instance import InstMeta, InstCat, Instance
from .runner import AbstractAsyncRunner, AsyncParallelRunner
from .parse import QueryFormParser, InstanceParser

# Solana saga

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
    def search(self, query: str, inst_cat: InstCat) -> list[InstMeta]:
        """
        搜索实例
        """
        raise NotImplementedError

    @abc.abstractmethod
    def query(self, **kwargs) -> list[InstMeta]:
        """
        查询实例
        """
        raise NotImplementedError


class PhoneDBHTTPSession(AbstractPhoneDBSession):
    BASE_URL = "https://phonedb.net/"

    def __init__(self, runner: AbstractAsyncRunner = AsyncParallelRunner(), **kwargs):
        self.runner = runner
        self.session = Client(**kwargs)
        self.queries_cache = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    async def get_latest_id(self, inst_cat: InstCat) -> int:
        response = await self.session.retryable_get(
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

    async def get_data(self, inst_meta: InstMeta) -> Instance:
        response = await self.session.retryable_get(
            f"https://phonedb.net/index.php",
            params={
                "m": inst_meta.inst_cat,
                "id": inst_meta.inst_id,
                "d": "detailed_specs"
            }
        )
        return await InstanceParser(inst_meta, await response.text()).parse()

    async def get_data_multi(self, inst_metas: list[InstMeta]) -> AsyncGenerator[Instance]:
        for inst_meta in inst_metas:
            self.runner.register(
                self.get_data(inst_meta)
            )

        async for data in self.runner.run():
            yield data

    async def search(self, query: str, inst_cat: InstCat) -> AsyncGenerator[InstMeta]:
        # 为初始请求添加重试
        response = await self.session.retryable_post(
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

        tree = lxml.etree.HTML(await response.text())
        results_count = int(tree.xpath("/html/body/div[4]/text()[1]")[0].split(" ")[0])

        # Do-While
        for i in range(1, math.ceil(results_count / 29)):
            filter_arg = i * 29
            # 为分页请求添加重试
            self.runner.register(self.session.retryable_post(
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
            tree = lxml.etree.HTML(await response.text())
            for j in tree.xpath("/html/body/div[5]")[0].getchildren():
                if j.tag != "div" or j.get("style"):
                    continue
                yield InstMeta(
                    inst_cat=inst_cat,
                    inst_id=int(urllib.parse.parse_qs(
                        urllib.parse.urlparse(j.getchildren()[0].getchildren()[0].get("href")).query
                    )["id"][0])
                )

    async def query(self, inst_cat: InstCat, params: dict) -> AsyncGenerator[InstMeta]:
        # 为初始请求添加重试
        response = await self.session.retryable_get(
            f"https://phonedb.net/index.php",
            params={
                "m": inst_cat,
                "s": "query",
                "d": "detailed_specs"
            }
        )

        payload = await QueryFormParser(await response.text()).parse(params)
        # 为POST请求添加重试
        response = await self.session.retryable_post(
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

        # Do-While
        for i in range(1, math.ceil(results_count / 29)):
            filter_arg = i * 29
            # 为分页请求添加重试
            self.runner.register(self.session.retryable_post(
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
