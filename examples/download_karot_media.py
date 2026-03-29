import asyncio

from karokit import Client


async def main() -> None:
    client = Client()
    await client.login(identifier="YOUR_IDENTIFIER", password="YOUR_PASSWORD")
    post = await client.get_post(123456789)
    print("Post:", post)
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
