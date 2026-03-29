import asyncio

from karokit import Client


async def main() -> None:
    client = Client()
    await client.login(identifier="YOUR_IDENTIFIER", password="YOUR_PASSWORD")
    await client.create_karot("hello from karokit")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
