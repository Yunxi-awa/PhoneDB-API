import asyncio

from loguru import logger

from phonedb_api import *


async def main():
    db = DatabaseTinyDB(
        r"E:\Code\Python\PhoneDB-API\cache\database.json",
        storage_cache_size=1024,
        query_cache_size=64,
        escape_forward_slashes=False
    )

    async with PhoneDB(session_config=SessionConfig(kwargs={"verify": False}), database=db) as s:
        logger.debug(await s.get_latest_id(ItemCategory.DEVICE))

        item_ = await s.get_item_smartly(ItemInfo(ItemCategory.DEVICE, 24990))
        logger.debug(item_.translated(LangClassZhCN()))

    async with MultiPhoneDB(session_config=SessionConfig(kwargs={"verify": False}), database=db) as s:
        logger.debug(await s.get_latest_id(ItemCategory.DEVICE))
        await s.multi_ensure_item_cached([ItemInfo(ItemCategory.DEVICE, i) for i in range(20000, 24991)])


if __name__ == "__main__":
    asyncio.run(main())
