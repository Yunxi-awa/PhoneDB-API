import atexit
import ujson
from loguru import logger
from tinydb import TinyDB, Query, JSONStorage
from tinydb.storages import MemoryStorage
from tinydb.middlewares import CachingMiddleware
from abc import ABC, abstractmethod

from .item import Item, ItemInfo


class Database(ABC):
    @abstractmethod
    def cache_item(self, item: Item):
        pass

    @abstractmethod
    def query_item(self, item_info: ItemInfo) -> Item | None:
        pass


class DatabaseTinyDB(Database, TinyDB):
    def __init__(self, db_path: str, storage_cache_size: int = 1024, query_cache_size: int = 64, **kwargs):
        atexit.register(self.close)

        middleware = CachingMiddleware(JSONStorage)
        middleware.WRITE_CACHE_SIZE = storage_cache_size
        super().__init__(db_path, storage=middleware, **kwargs)

        self.db_path = db_path
        self.query_cache_size = query_cache_size

    def cache_item(self, item: Item):
        table = self.table(item.item_info.category, cache_size=self.query_cache_size)
        try:
            table.insert(item.parsed)
            logger.debug(f"缓存 {item.item_info} 成功")
        except Exception as e:
            logger.error(f"缓存 {item.item_info} 成功, 错误信息 {e}, 错误数据 {item.parsed}")

    def query_item(self, item_info: ItemInfo) -> Item | None:
        q = Query()
        table = self.table(item_info.category, cache_size=self.query_cache_size)
        results = table.search(q.id == item_info.id_spec)

        if len(results) == 0:
            logger.debug(f"查询 {item_info} 结果: 无")
            return None
        elif len(results) == 1:
            logger.debug(f"查询 {item_info} 结果: {results[0]}")
            return Item(item_info, parsed=results[0])
        else:
            raise RuntimeError(f"查询 {item_info} 结果过多.")
