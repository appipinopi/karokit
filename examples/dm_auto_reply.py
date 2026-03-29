import asyncio

from karokit import Client


async def main() -> None:
    client = Client()
    await client.login(identifier="YOUR_IDENTIFIER", password="YOUR_PASSWORD")
    print("Implement your own DM auto reply loop with get_dm_groups/get_dm_messages/send_dm_message")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
