import asyncio
import urllib.parse

import lxml.etree
from loguru import logger

from .config import SessionConfig
from .database import Database
from .exception import ResponseError
from .item import Item, ItemCategory, ItemInfo
from .session import EnhancedAsyncSession


class PhoneDB:
    def __init__(
            self,
            database: Database,
            session_config: SessionConfig = None,
    ):
        self._db = database
        self._session = EnhancedAsyncSession(session_config=session_config)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self) -> None:
        await self._session.close()

    async def get_latest_id(self, category: ItemCategory = None) -> int:
        # 构建目标URL，category参数用于指定要查询的分类(设备/固件/处理器等)
        url = f"https://phonedb.net/index.php?m={category}&s=list"

        text = await self._fetch_html_text(url)

        # 使用lxml解析HTML内容
        tree = lxml.etree.HTML(text)

        # 从查询参数中提取ID并转换为整数返回

        # 解析URL中的查询参数
        # 通过XPath定位页面中最新条目的链接
        # 这里查找的是页面中第一个设备/固件/处理器的链接
        href = tree.xpath("/html/body/div[5]/div[1]/div[1]/a")[0].get("href")
        parsed_url = urllib.parse.urlparse(href)
        query = urllib.parse.parse_qs(parsed_url.query)
        return int(query["id"][0])

    async def _fetch_html_text(self, url: str) -> str:
        """处理请求获取逻辑"""
        response = await self._session.get(url)
        if response is None:
            raise ResponseError(f"无返回信息.")
        response.raise_for_status()
        if len(response.text) <= 4096:
            raise ResponseError(f"返回信息过短: {len(response.text)}\n{response.text}")
        return response.text

    async def get_item_from_web(self, item_info: ItemInfo) -> Item:
        url = f"https://phonedb.net/index.php?m={item_info.category}&id={item_info.id_spec}&d=detailed_specs"
        return Item(item_info, await self._fetch_html_text(url))

    async def get_item_smartly(self, item_info: ItemInfo) -> Item:
        item = self._db.query_item(item_info)  # 优先尝试从缓存读取
        if item is None:
            item = await self.get_item_from_web(item_info)  # 失败时再从网络获取
            self._db.cache_item(item)
        return item

    async def ensure_item_cached(self, item_info: ItemInfo):
        item = self._db.query_item(item_info)
        if item is None:
            item = await self.get_item_from_web(item_info)
            self._db.cache_item(item)


class MultiPhoneDB(PhoneDB):
    def __init__(
            self,
            session_config: SessionConfig = None,
            database: Database = None,  # 缓存地址
            max_workers: int = 16,
    ):
        if session_config is None:
            session_config = SessionConfig()
        session_config.kwargs["max_clients"] = max_workers
        super().__init__(database, session_config)
        self.max_workers = max_workers

    async def multi_get_item_smartly(self, item_infos: list[ItemInfo]) -> list[Item]:
        """
        并发获取多个ItemInfo
        :param item_infos: 多个ItemInfo
        :return: 多个Item
        """
        semaphore = asyncio.Semaphore(self.max_workers)

        async def worker(item_info: ItemInfo):
            async with semaphore:
                return await self.get_item_smartly(item_info)

        return await asyncio.gather(*[worker(item_info) for item_info in item_infos])

    async def multi_ensure_item_cached(self, item_infos: list[ItemInfo]):
        """
        并发缓存多个ItemInfo
        :param item_infos: 多个ItemInfo
        :return: None
        """
        semaphore = asyncio.Semaphore(self.max_workers)

        async def worker(item_info: ItemInfo):
            async with semaphore:
                await self.ensure_item_cached(item_info)
                logger.info(f"{item_info}: 缓存完毕.")

        await asyncio.gather(*[worker(item_info) for item_info in item_infos])
