import asyncio
from ce3 import Assistant

async def main():
    assistant = Assistant()
    print("Assistant initialized successfully")

if __name__ == "__main__":
    asyncio.run(main())
