import asyncio
import sys

sys.path.insert(0, "D:/AI_MIYA_Facyory/MIYA/Miya")


async def test():
    from memory import store_auto

    await store_auto(
        "【测试】这是弥娅的情绪记录", user_id="1523878699", tags=["测试"], priority=0.5
    )
    print("存储成功!")


asyncio.run(test())
