import asyncio

from loguru import logger

from phonedb_api import *


async def main():
    db = DatabaseTinyDB(
        r"..\cache\phonedb.json",
        storage_cache_size=1024,
        query_cache_size=64,
        escape_forward_slashes=False
    )

    session = WebSessionCurlCffi(session_config=SessionConfig(kwargs={"verify": False}))

    async with PhoneDB(session=session, database=db) as phone_db:
        logger.debug(await phone_db.get_latest_id(ItemCategory.DEVICE))

        item_ = await phone_db.get_item_smartly(ItemInfo(ItemCategory.DEVICE, 24990))
        logger.debug(item_.translated(LangClassZhCN()))

    db2 = DatabaseTinyDB(
        r"..\cache\phonedb.json",
        storage_cache_size=1024,
        query_cache_size=64,
        escape_forward_slashes=False
    )

    session2 = WebSessionCurlCffi(session_config=SessionConfig(kwargs={"verify": False}))

    async with MultiPhoneDB(session=session2, database=db2) as multi_phone_db:
        logger.debug(await multi_phone_db.get_latest_id(ItemCategory.DEVICE))
        await multi_phone_db.multi_ensure_item_cached([ItemInfo(ItemCategory.DEVICE, i) for i in range(20000, 24991)])


if __name__ == "__main__":
    asyncio.run(main())
