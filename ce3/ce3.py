import asyncio
import importlib
import inspect
import json
import logging
import os
import pkgutil
import sys
import time
import uuid

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import aiofiles
import anthropic
import tiktoken
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner

from config import Config
from prompts.system_prompts import SystemPrompts
from tools.base import BaseTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ContextSummary:
    """Maintains conversation context and summary"""
    key_points: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    important_context: str = "No context available"
    last_updated: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def add_key_point(self, point: str):
        """Add a new key point, maintaining only the most recent points"""
        self.key_points.append(point)
        self.key_points = self.key_points[-5:]  # Keep last 5 points
        
    def add_decision(self, decision: str):
        """Add a new decision, maintaining only the most recent decisions"""
        self.decisions.append(decision)
        self.decisions = self.decisions[-3:]  # Keep last 3 decisions
        
    def update_context(self, current_messages: List[Dict[str, Any]]):
        """Update the important context based on recent messages"""
        context_points = []
        for msg in current_messages[-10:]:  # Look at last 10 messages
            if isinstance(msg.get('content'), str):
                if any(kw in msg['content'].lower() for kw in ['important', 'key', 'crucial', 'essential']):
                    context_points.append(msg['content'])
        
        if context_points:
            self.important_context = " ".join(context_points[-3:])  # Keep last 3 important points
        self.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class Memory:
    """Manages conversation history and context summaries with compression"""
    def __init__(self):
        self.full_history: List[Dict[str, Any]] = []
        self.summary: Optional[ContextSummary] = None
        self.total_tokens: int = 0
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.MAX_TOKEN_THRESHOLD = 3000
        self.MAX_MESSAGES = 50
        self.TIME_THRESHOLD = 3600
        self.PRESERVE_MESSAGES = 10
        self.last_compression = time.time()

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a new message to the conversation history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "tokens": len(self.encoder.encode(content)),
            "metadata": metadata or {}
        }
        self.full_history.append(message)
        self.total_tokens += message["tokens"]
        self._check_compression_triggers()

    def _check_compression_triggers(self):
        """Check if any compression triggers are met"""
        current_time = time.time()
        total_tokens = self.total_tokens
        
        should_compress = (
            total_tokens > self.MAX_TOKEN_THRESHOLD or
            len(self.full_history) > self.MAX_MESSAGES or
            (current_time - self.last_compression) > self.TIME_THRESHOLD
        )
        
        if should_compress:
            self._compress_context()

    def _compress_context(self):
        """Compress conversation history while preserving important context"""
        if len(self.full_history) <= self.PRESERVE_MESSAGES:
            return
            
        # Preserve recent messages
        recent_messages = self.full_history[-self.PRESERVE_MESSAGES:]
        older_messages = self.full_history[:-self.PRESERVE_MESSAGES]
        
        # Create summary of less important messages
        summary = self._generate_summary(older_messages)
        summary_message = {
            "role": "system",
            "content": summary,
            "timestamp": time.time(),
            "tokens": len(self.encoder.encode(summary)),
            "metadata": {"is_summary": True}
        }
        
        # Replace older messages with summary
        self.full_history = [summary_message] + recent_messages
        self.total_tokens = sum(msg["tokens"] for msg in self.full_history)
        self.last_compression = time.time()

    def _generate_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Generate a concise summary of multiple messages"""
        summary_parts = ["Previous conversation summary:"]
        
        # Group messages by role
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]
        
        if user_messages:
            summary_parts.append(f"- User made {len(user_messages)} requests")
        if assistant_messages:
            summary_parts.append(f"- Assistant provided {len(assistant_messages)} responses")
        
        return "\n".join(summary_parts)

    async def save_to_file(self, filename: str):
        """Save conversation history to a file"""
        try:
            async with aiofiles.open(filename, 'w') as f:
                await f.write(json.dumps({
                    'conversation_history': self.full_history,
                    'total_tokens': self.total_tokens,
                    'last_compression': self.last_compression
                }, indent=2))
            return True
        except Exception as e:
            logger.error(f"Error saving memory: {str(e)}")
            return False

    async def load_from_file(self, filename: str):
        """Load conversation history from a file"""
        try:
            async with aiofiles.open(filename, 'r') as f:
                data = json.loads(await f.read())
                self.full_history = data['conversation_history']
                self.total_tokens = data['total_tokens']
                self.last_compression = data['last_compression']
            return True
        except Exception as e:
            logger.error(f"Error loading memory: {str(e)}")
            return False

class PromptCache:
    """Manages caching of prompt responses"""
    def __init__(self):
        self.cache = {}
        self.hits = 0
        self.misses = 0
        
    def get(self, messages, tools, temp, system):
        key = str((messages, tools, temp, system))
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None
        
    def put(self, messages, tools, temp, system, response):
        key = str((messages, tools, temp, system))
        self.cache[key] = response

class Assistant:
    """Main assistant class with integrated token management, memory, and caching"""
    def __init__(self):
        if not getattr(Config, 'ANTHROPIC_API_KEY', None):
            raise ValueError("No ANTHROPIC_API_KEY found in environment variables")
        
        self.client = anthropic.AsyncAnthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.memory = Memory()
        self.cache = PromptCache()
        self.console = Console()
        self.thinking_enabled = getattr(Config, 'ENABLE_THINKING', False)
        self.temperature = getattr(Config, 'DEFAULT_TEMPERATURE', 0.7)
        self.total_tokens_used = 0
        self.tools = self._load_tools()

    def _load_tools(self) -> List[Dict[str, Any]]:
        """Load available tools from the tools directory"""
        tools = []
        tools_path = getattr(Config, 'TOOLS_DIR', None)
        
        if tools_path is None:
            self.console.print("[red]TOOLS_DIR not set in Config[/red]")
            return tools

        try:
            for module_info in pkgutil.iter_modules([str(tools_path)]):
                if module_info.name == 'base':
                    continue
                
                try:
                    module = importlib.import_module(f'tools.{module_info.name}')
                    self._extract_tools_from_module(module, tools)
                except ImportError as e:
                    logger.error(f"Error loading tool {module_info.name}: {str(e)}")
                except Exception as e:
                    logger.error(f"Error initializing tool {module_info.name}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error loading tools: {str(e)}")
            
        return tools

    def _extract_tools_from_module(self, module, tools: List[Dict[str, Any]]) -> None:
        """Extract tools from a module"""
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and issubclass(obj, BaseTool) and obj != BaseTool):
                try:
                    tool_instance = obj()
                    tools.append({
                        "name": tool_instance.name,
                        "description": tool_instance.description,
                        "input_schema": tool_instance.input_schema
                    })
                    self.console.print(f"[green]Loaded tool:[/green] {tool_instance.name}")
                except Exception as e:
                    logger.error(f"Error initializing tool {name}: {str(e)}")

    def _display_token_usage(self, usage):
        """Display token usage with visual indicators"""
        used_percentage = (self.total_tokens_used / Config.MAX_CONVERSATION_TOKENS) * 100
        remaining_tokens = max(0, Config.MAX_CONVERSATION_TOKENS - self.total_tokens_used)
        
        bar_width = 40
        filled = int(used_percentage / 100 * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        color = "green"
        if used_percentage > 75:
            color = "yellow"
        if used_percentage > 90:
            color = "red"
            
        self.console.print(f"[{color}][{bar}] {used_percentage:.1f}%[/{color}]")
        
        if remaining_tokens < 20000:
            self.console.print(f"[bold red]Warning: Only {remaining_tokens:,} tokens remaining![/bold red]")
        
        self.console.print("---")

    async def chat(self, user_input: str) -> str:
        """Handle chat interaction"""
        try:
            # Add user message to memory
            self.memory.add_message("user", user_input)
            
            # Get completion
            if self.thinking_enabled:
                with Live(Spinner("dots", text="Thinking..."), refresh_per_second=8):
                    response = await self._get_completion()
            else:
                response = await self._get_completion()
                
            # Add assistant response to memory
            self.memory.add_message("assistant", response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            return f"Error: {str(e)}"

    async def _get_completion(self):
        """Get completion from the API"""
        try:
            response = await self.client.messages.create(
                model=Config.MODEL,
                max_tokens=min(
                    Config.MAX_TOKENS,
                    Config.MAX_CONVERSATION_TOKENS - self.total_tokens_used
                ),
                temperature=self.temperature,
                tools=self.tools,
                messages=self.memory.full_history,
                system=f"{SystemPrompts.DEFAULT}\n\n{SystemPrompts.TOOL_USAGE}"
            )
            
            # Update token usage
            if hasattr(response, 'usage'):
                self.total_tokens_used += response.usage.input_tokens + response.usage.output_tokens
                self._display_token_usage(response.usage)
                
            return response.content[0].text if response.content else "No response content"
            
        except Exception as e:
            logger.error(f"Error getting completion: {str(e)}")
            return f"Error: {str(e)}"

    async def save_context(self):
        """Save current context to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"context_{timestamp}.json"
            await self.memory.save_to_file(filename)
            self.console.print(f"[green]Context saved to {filename}[/green]")
        except Exception as e:
            logger.error(f"Error saving context: {str(e)}")
            self.console.print(f"[red]Error saving context: {str(e)}[/red]")

    async def shutdown(self):
        """Cleanup before shutdown"""
        await self.save_context()
        self.console.print("[green]Shutting down...[/green]")

async def main():
    """Main entry point"""
    try:
        assistant = Assistant()
        
        # Example usage
        while True:
            user_input = input("You: ")
            if user_input.lower() == 'quit':
                await assistant.shutdown()
                break
                
            response = await assistant.chat(user_input)
            print(f"Assistant: {response}")
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())