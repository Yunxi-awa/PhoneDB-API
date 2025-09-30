from phonedb_api import *


async def main():
    async with PhoneDBHTTPSession(runner=AsyncParallelRunner(max_workers=32)) as session:
        print(await session.get_data(InstMeta(InstCat.DEVICE, 1)))
        async for i in session.search("8Gen3", InstCat.DEVICE):
            print(i)
        metas = []
        async for i in session.query(
                InstCat.DEVICE,
                params={
                    "CPU": [
                        "Snapdragon 865 5G SM8250",
                        "Snapdragon 865+ 5G SM8250-AB",
                        "Snapdragon 870 5G SM8250-AC"
                    ]
                }
        ):
            metas.append(i)
        async for i in session.get_data_multi(metas):
            print(i.data["Introduction"]["Model"][0],"   ", i.data["Application processor, Chipset"]["CPU"][0])


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
