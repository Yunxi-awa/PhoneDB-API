import atexit
from abc import ABC, abstractmethod

from loguru import logger
from tinydb import TinyDB, Query, JSONStorage
from tinydb.middlewares import CachingMiddleware

from .item import Item, ItemInfo


class Database(ABC):
    """
    数据库基类
    """

    @abstractmethod
    def cache_item(self, item: Item):
        """
        缓存Item
        :param item: Item
        :return:
        """
        pass

    @abstractmethod
    def query_item(self, item_info: ItemInfo) -> Item | None:
        """
        查询Item
        :param item_info: ItemInfo
        :return: Item | None
        """
        pass

    def close(self):
        """
        关闭数据库
        :return:
        """
        pass


class DatabaseTinyDB(TinyDB, Database):
    """
    TinyDB数据库实现
    """

    class EnhancedCachingMiddleware(CachingMiddleware):
        """
        增强的缓存中间件，增加了缓存写入硬盘的日志输出以及优化了write_cache_size的配置方式。
        :param storage_cls: 原始的Storage类
        :param write_cache_size: 缓存写入硬盘的大小，默认1024条
        """

        def __init__(self, storage_cls, write_cache_size=1024):
            super().__init__(storage_cls)
            self.WRITE_CACHE_SIZE = write_cache_size

        def flush(self):
            super().flush()
            logger.debug(f"数据库缓存已写入硬盘。")

    def __init__(
            self,
            db_path: str = "phonedb.json",
            storage_cache_size: int = 1024,
            query_cache_size: int = 64,
            **kwargs
    ):
        atexit.register(self.close)

        super().__init__(
            db_path,
            storage=self.EnhancedCachingMiddleware(
                storage_cls=JSONStorage,
                write_cache_size=storage_cache_size
            ),
            **kwargs
        )

        self.db_path = db_path
        self.query_cache_size = query_cache_size

    def cache_item(self, item: Item):
        table = self.table(item.item_info.category, cache_size=self.query_cache_size)
        try:
            table.insert(item.parsed)
            logger.debug(f"缓存 {item.item_info} 成功")
        except Exception as e:
            logger.error(f"缓存 {item.item_info} 失败, 错误信息 {e}, 错误数据 {item.parsed}")

    def query_item(self, item_info: ItemInfo) -> Item | None:
        q = Query()
        table = self.table(item_info.category, cache_size=self.query_cache_size)
        results = table.search(q.id == item_info.id_spec)

        if len(results) == 0:
            logger.debug(f"查询 {item_info} 结果: 无。")
            return None
        elif len(results) == 1:
            logger.debug(f"查询 {item_info} 成功。")
            return Item(item_info, parsed=results[0])
        else:
            raise RuntimeError(f"查询 {item_info} 结果过多。")
