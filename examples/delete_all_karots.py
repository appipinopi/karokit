import asyncio

from karokit import Client


async def main() -> None:
    client = Client()
    await client.login(identifier="YOUR_IDENTIFIER", password="YOUR_PASSWORD")
    print("Implement your own delete loop using get_user_karots + delete_post")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
