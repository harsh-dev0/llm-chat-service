import asyncio

from app.services.llm_service import complete, stream


async def main() -> None:
    print(await complete([{"role": "user", "content": "Say hi in five words."}]))
    async for tok in stream([{"role": "user", "content": "Count 1 to 5."}]):
        print(tok, end="", flush=True)
    print()


asyncio.run(main())