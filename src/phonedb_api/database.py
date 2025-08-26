import atexit
import ujson
from loguru import logger
from tinydb import TinyDB, Query
from tinydb.storages import MemoryStorage
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
    def __init__(self, db_path: str, lazy_storage: bool = False, cache_size: int = 64, *args, **kwargs):
        atexit.register(self.close)
        if lazy_storage:
            super().__init__(storage=MemoryStorage, *args, **kwargs)
        else:
            super().__init__(db_path, *args, **kwargs)
        self.db_path = db_path
        self.cache_size = cache_size

    def close(self) -> None:
        data = {table_name: self.table(table_name).all() for table_name in self.tables()}
        logger.debug(f"数据库总大小: {sum([len(table) for table in data.values()])}")
        logger.debug(f"数据库表大小: {[len(table) for table in data.values()]}")
        logger.debug(f"数据库表名: {self.tables()}")
        if self.db_path is not None:
            with open(self.db_path, "w") as f:
                f.write(ujson.dumps(data))
        super().close()

    def cache_item(self, item: Item):
        table = self.table(item.item_info.category, cache_size=self.cache_size)
        try:
            table.insert(item.parsed)
            logger.debug(f"缓存 {item.item_info} 成功")
        except Exception as e:
            logger.error(f"缓存 {item.item_info} 成功, 错误信息 {e}, 错误数据 {item.parsed}")

    def query_item(self, item_info: ItemInfo) -> Item | None:
        q = Query()
        table = self.table(item_info.category, cache_size=self.cache_size)
        results = table.search(q.id == item_info.id_spec)

        if len(results) == 0:
            logger.debug(f"查询 {item_info} 结果: 无")
            return None
        elif len(results) == 1:
            logger.debug(f"查询 {item_info} 结果: {results[0]}")
            return Item(item_info, parsed=results[0])
        else:
            raise RuntimeError(f"查询 {item_info} 结果过多.")
