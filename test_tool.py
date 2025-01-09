import asyncio
import os
from rich.console import Console
from tools.filecontentreadertool import FileContentReaderTool
from tools.contextmanager import ContextManager
from config import Config

console = Console()

async def main():
    # Test tool output styling
    console.print("\n[bold]Testing tool output styling...[/bold]")
    tool = FileContentReaderTool()
    result = tool.execute(file_paths=['test_tool.py'])
    # Parse the result text as Rich markup
    from rich.markup import render
    console.print(render(result["text"]))
    
    # Test summary generation
    console.print("\n[bold]Testing summary generation...[/bold]")
    context_manager = ContextManager()
    context = "Please summarize this test context for me."
    summary = await context_manager.generate_summary(context)
    console.print(f"[cyan]Summary:[/cyan] {summary}")

if __name__ == '__main__':
    asyncio.run(main())
