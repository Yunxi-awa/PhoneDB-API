from phonedb_api import *


async def main():
    async with PhoneDBHTTPSession(runner=AsyncParallelRunner(max_workers=32)) as session:
        print(await session.get_data(InstMeta(InstCat.DEVICE, 1)))
        async for i in session.search("8Gen3", InstCat.DEVICE):
            print(i)
        async for i in session.query(
                InstCat.DEVICE,
                params={
                "CPU": [
                    "Snapdragon 8 Gen 3 SM8650-AB",
                    "Dimensity 9300 MT6989"
                ]
            }
        ):
            print(i)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
