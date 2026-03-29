import asyncio

from karokit import Client, StreamingClient


async def main() -> None:
    client = Client()
    await client.login(identifier="YOUR_IDENTIFIER", password="YOUR_PASSWORD")

    stream = StreamingClient(client)
    try:
        async for notification in stream.realtime_notifications():
            print(notification)
    finally:
        await stream.realtime.disconnect()
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
