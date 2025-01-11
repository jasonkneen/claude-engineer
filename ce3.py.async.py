import asyncio
import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from typing import List, Dict, Any
import importlib
import inspect
import pkgutil
import os
import json
import sys
import logging

from config import Config
from tools.base import BaseTool
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.styles import Style
from prompts.system_prompts import SystemPrompts

logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')

class Assistant:
    def __init__(self):
        if not getattr(Config, 'ANTHROPIC_API_KEY', None):
            raise ValueError("No ANTHROPIC_API_KEY found in environment variables")
        self.client = anthropic.AsyncAnthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.conversation_history = []
        self.console = Console()
        self.thinking_enabled = getattr(Config, 'ENABLE_THINKING', False)
        self.temperature = getattr(Config, 'DEFAULT_TEMPERATURE', 0.7)
        self.total_tokens_used = 0
        self.tools = self._load_tools()

        def _load_tools(self) -> List[Dict[str, Any]]:
            """Load available tools. Currently returns an empty list."""
            return []

        # [Previous methods remain unchanged]
    
    async def _get_completion(self):
        try:
            response = await self.client.messages.create(
                model=Config.MODEL,
                max_tokens=min(Config.MAX_TOKENS, Config.MAX_CONVERSATION_TOKENS - self.total_tokens_used),
                temperature=self.temperature,
                tools=self.tools,
                messages=self.conversation_history,
                system=f"{SystemPrompts.DEFAULT}\n\n{SystemPrompts.TOOL_USAGE}"
            )

            if hasattr(response, 'usage') and response.usage:
                message_tokens = response.usage.input_tokens + response.usage.output_tokens
                self.total_tokens_used += message_tokens
                self._display_token_usage(response.usage)

            if response.stop_reason == "tool_use":
                # Handle tool use case
                tool_results = []
                for content_block in response.content:
                    if content_block.type == "tool_use":
                        result = self._execute_tool(content_block)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": result if isinstance(result, (list, dict)) else [{"type": "text", "text": str(result)}]
                        })
                
                self.conversation_history.extend([
                    {"role": "assistant", "content": response.content},
                    {"role": "user", "content": tool_results}
                ])
                return await self._get_completion()

            # Regular response
            if response.content:
                final_content = response.content[0].text
                self.conversation_history.append({"role": "assistant", "content": response.content})
                return final_content
            return "No response content available."

        except Exception as e:
            logging.error(f"Error in _get_completion: {str(e)}")
            return f"Error: {str(e)}"

    async def chat(self, user_input):
        if isinstance(user_input, str):
            if user_input.lower() == 'refresh':
                self.refresh_tools()
                return "Tools refreshed successfully!"
            elif user_input.lower() == 'reset':
                await self.reset()
                return "Conversation reset!"
            elif user_input.lower() == 'quit':
                return "Goodbye!"

        try:
            self.conversation_history.append({"role": "user", "content": user_input})
            response = await self._get_completion()
            return response
        except Exception as e:
            logging.error(f"Error in chat: {str(e)}")
            return f"Error: {str(e)}"

    async def reset(self):
        self.conversation_history = []
        self.total_tokens_used = 0
        self.console.print("\n[bold green]🔄 Assistant memory has been reset![/bold green]")
        welcome_text = """
# Claude Engineer v3. A self-improving assistant framework with tool creation

Type 'refresh' to reload available tools
Type 'reset' to clear conversation history
Type 'quit' to exit

Available tools:
"""
        self.console.print(Markdown(welcome_text))
        self.display_available_tools()

async def main():
    console = Console()
    style = Style.from_dict({'prompt': 'orange'})
    session = PromptSession(style=style)

    try:
        assistant = Assistant()
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        console.print("Please ensure ANTHROPIC_API_KEY is set correctly.")
        return

    welcome_text = """
# Claude Engineer v3. A self-improving assistant framework with tool creation

Type 'refresh' to reload available tools
Type 'reset' to clear conversation history
Type 'quit' to exit

Available tools:
"""
    console.print(Markdown(welcome_text))
    assistant.display_available_tools()

    while True:
        try:
            user_input = await session.prompt_async("You: ")
            user_input = user_input.strip()

            if user_input.lower() == 'quit':
                console.print("\n[bold blue]👋 Goodbye![/bold blue]")
                break

            response = await assistant.chat(user_input)
            console.print("\n[bold purple]Claude Engineer:[/bold purple]")
            if isinstance(response, str):
                safe_response = response.replace('[', '\\[').replace(']', '\\]')
                console.print(safe_response)
            else:
                console.print(str(response))

        except KeyboardInterrupt:
            continue
        except EOFError:
            break

if __name__ == "__main__":
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(main())
        finally:
            loop.close()
    except Exception as e:
        logging.error(f"Error in main execution: {str(e)}")
        raise