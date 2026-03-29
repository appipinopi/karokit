import asyncio

from karokit import Client


async def main() -> None:
    client = Client()
    await client.login(identifier="YOUR_IDENTIFIER", password="YOUR_PASSWORD")
    page = await client.get_timeline(page=1)
    print(page)
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
