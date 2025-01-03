import asyncio
from ce3_with_cache import Assistant
from rich.console import Console

async def test_caching():
    console = Console()
    assistant = Assistant()
    
    # Test 1: First request (should miss cache)
    console.print("\n[bold]Test 1: First request (should miss cache)[/bold]")
    response1 = await assistant.chat("What is 2+2?")
    console.print(f"Response 1: {response1}")
    
    # Test 2: Same request (should hit cache)
    console.print("\n[bold]Test 2: Same request (should hit cache)[/bold]")
    response2 = await assistant.chat("What is 2+2?")
    console.print(f"Response 2: {response2}")
    
    # Test 3: Different request (should miss cache)
    console.print("\n[bold]Test 3: Different request (should miss cache)[/bold]")
    response3 = await assistant.chat("What is 3+3?")
    console.print(f"Response 3: {response3}")
    
    await assistant.shutdown()

def main():
    asyncio.run(test_caching())

if __name__ == "__main__":
    main()