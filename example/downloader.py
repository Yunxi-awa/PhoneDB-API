from phonedb_api import *


async def main():
    async with PhoneDBHTTPSession(
            runner=AsyncParallelRunner(max_workers=64),
            database=PickleDatabase("phonedb.pkl"),
            verify=False
    ) as session:

        # 获取最新的设备ID
        # l = await session.get_latest_id(InstCat.DEVICE)

        # 下载所有设备数据
        # async for _ in session.get_data_multi([InstMeta(InstCat.DEVICE, i) for i in range(1, l + 1)]):
        #     pass

        # 网络搜索所有包含"8Gen3"的设备
        # async for i in session.search_website("8Gen3", InstCat.DEVICE):
        #     print(i)

        # 查询数据库中所有包含"865"的设备
        # metas = []
        # async for i in session.query_database(InstCat.DEVICE, params={
        #     "CPU": [
        #         "Snapdragon 865 5G SM8250",
        #         "Snapdragon 865+ 5G SM8250-AB",
        #     ]
        # }):
        #     metas.append(i)
        # print(metas)

        metas = []
        async for i in session.query_database(InstCat.DEVICE, params={
            "Application processor, Chipset": {
                "CPU": [
                    Query("Snapdragon 865"),
                    Query("Snapdragon 865+"),
                ]
            },
            "Display": {
                "Resolution": [
                    Query("1440x2560", QueryStrategy.DISPLAY_RESOLUTION_AT_LEAST),
                ],
                "Display Refresh Rate": [
                    Query("90", QueryStrategy.WITHOUT_UNIT_AT_LEAST),
                ],
            },
            # "Operative Memory": {
            #     "RAM Capacity": [
            #         Query("8192"),
            #     ]
            # }

        }):
            metas.append(i)
        print(metas)
        for i in metas:
            print(i.data["Introduction"]["Model"][0],
                  "   ", i.data["Application processor, Chipset"]["CPU"][0],
                  "   ", i.data["Display"]["Resolution"],
                  "   ", i.data["Display"].get("Display Refresh Rate", ["N/A"])[0],
                  "   ", i.data["Display"].get("Display Type", ["N/A"])[0],
                  "   ", i.data["Operative Memory"].get("RAM Capacity", ["N/A"])[0],
                  )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
