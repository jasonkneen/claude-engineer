#!/usr/bin/env python3
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
from prompt_toolkit import prompt
from prompt_toolkit.styles import Style

from config import Config
from tools.base import BaseTool
from prompts.system_prompts import SystemPrompts
from memory_manager import MemoryManager, MemoryBlock, SignificanceType, MemoryLevel
from memory_server_client import MemoryServerClient

# Configure logging
logging.basicConfig(level=logging.ERROR, format="%(levelname)s: %(message)s")

class Assistant:
    def __init__(self):
        # Initialize console first
        self.console = Console()

        if not getattr(Config, "ANTHROPIC_API_KEY", None):
            raise ValueError("No ANTHROPIC_API_KEY found in environment variables")

        # Initialize Anthropic client
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

        # Initialize memory server client if enabled
        self.memory_client = None
        if getattr(Config, "ENABLE_MEMORY_SERVER", False):
            try:
                self.memory_client = MemoryServerClient(
                    host=getattr(Config, "MEMORY_SERVER_HOST", "localhost"),
                    port=getattr(Config, "MEMORY_SERVER_PORT", 8000)
                )
                self.console.print("[green]Connected to memory server[/green]")
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not connect to memory server: {e}[/yellow]")

        # Initialize memory system with configurable limits
        self.memory_manager = MemoryManager(
            working_memory_limit=getattr(Config, "WORKING_MEMORY_LIMIT", 8192),
            archival_memory_limit=getattr(Config, "ARCHIVAL_MEMORY_LIMIT", 512000),
            similarity_threshold=getattr(Config, "MEMORY_SIMILARITY_THRESHOLD", 0.85),
            cleanup_interval=getattr(Config, "MEMORY_CLEANUP_INTERVAL", 1000),
            memory_server_client=self.memory_client,
            stats_callback=self._broadcast_memory_stats,
        )

        # Memory tracking
        self.last_recall_time = 0
        self.generation_count = 0
        self.promotion_count = 0
        self.demotion_count = 0
        self.merge_count = 0
        self.retrieval_count = 0

        # Anthropic settings
        self.conversation_history: List[Dict[str, Any]] = []
        self.thinking_enabled = getattr(Config, "ENABLE_THINKING", False)
        self.temperature = getattr(Config, "DEFAULT_TEMPERATURE", 0.7)
        self.total_tokens_used = 0

        # Load tools
        self.tools = self._load_tools()

    def display_available_tools(self):
        """Print a list of currently loaded tools."""
        self.console.print("\n[bold cyan]Available tools:[/bold cyan]")
        tool_names = [tool["name"] for tool in self.tools]
        if tool_names:
            formatted_tools = ", ".join(
                [f"🔧 [cyan]{name}[/cyan]" for name in tool_names]
            )
        else:
            formatted_tools = "No tools available."
        self.console.print(formatted_tools)
        self.console.print("\n---")

    def _broadcast_memory_stats(self, stats):
        """Handle memory stats updates and broadcast to all interfaces"""
        if not stats:
            return

        # Update web interface if memory client is available
        if self.memory_client:
            self.memory_client.broadcast_stats(stats)

        # Update CLI display
        self._display_cli_stats(stats)

    def _display_cli_stats(self, stats):
        """Display memory system statistics in CLI"""
        if not stats:
            return

        # Memory pools section
        pools_text = []
        for pool_name, pool_data in stats.get("pools", {}).items():
            utilization = pool_data.get("utilization", 0)
            color = "green"
            if utilization > 0.75:
                color = "yellow"
            if utilization > 0.90:
                color = "red"

            pool_info = f"{pool_name.replace('_', ' ').title()}: {pool_data.get('count', 0)} blocks, {pool_data.get('size', 0):,} tokens"
            if "utilization" in pool_data:
                pool_info += (
                    f" ([{color}]{pool_data['utilization']*100:.1f}%[/{color}])"
                )
            pools_text.append(pool_info)

        # Operations section
        ops = stats.get("operations", {})
        ops_text = [
            f"Generations: {stats.get('generations', 0):,}",
            f"Promotions: {ops.get('promotions', 0):,}",
            f"Demotions: {ops.get('demotions', 0):,}",
            f"Merges: {ops.get('merges', 0):,}",
            f"Retrievals: {ops.get('retrievals', 0):,}",
        ]

        # Nexus points section
        nexus = stats.get("nexus_points", {})
        nexus_text = [
            f"Total: {nexus.get('count', 0):,}",
            "Types: "
            + ", ".join(f"{k}: {v:,}" for k, v in nexus.get("types", {}).items()),
        ]

        # Performance section
        perf_text = [
            f"Total Tokens: {stats.get('total_tokens', 0):,}",
            f"Last Recall: {ops.get('avg_recall_time', 0):.2f}ms",
        ]

        # Create panels
        panels = [
            Panel("\n".join(pools_text), title="Memory Pools", border_style="blue"),
            Panel("\n".join(ops_text), title="Operations", border_style="green"),
            Panel("\n".join(nexus_text), title="Nexus Points", border_style="yellow"),
            Panel("\n".join(perf_text), title="Performance", border_style="cyan"),
        ]

        # Display all panels
        for panel in panels:
            self.console.print(panel)

    def _display_token_usage(self, usage):
        """Display a visual representation of token usage and remaining tokens."""
        used_percentage = (
            self.total_tokens_used / Config.MAX_CONVERSATION_TOKENS
        ) * 100
        remaining_tokens = max(
            0, Config.MAX_CONVERSATION_TOKENS - self.total_tokens_used
        )

        usage_text = [
            f"Total used: [bold]{self.total_tokens_used:,}[/bold] / [bold]{Config.MAX_CONVERSATION_TOKENS:,}[/bold]"
        ]

        bar_width = 40
        filled = int(used_percentage / 100 * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        color = "green"
        if used_percentage > 75:
            color = "yellow"
        if used_percentage > 90:
            color = "red"

        usage_text.append(
            f"[{color}]{bar}[/{color}] [bold]{used_percentage:.1f}%[/bold]"
        )

        if remaining_tokens < 20000:
            usage_text.append(
                f"[bold red]Warning: Only {remaining_tokens:,} tokens remaining![/bold red]"
            )

        panel = Panel("\n".join(usage_text), title="Token Usage", border_style="blue")
        self.console.print(panel)

    def _load_tools(self):
        """Dynamically load all tool classes from the tools directory."""
        tools = []
        tools_path = getattr(Config, "TOOLS_DIR", None)

        if tools_path is None:
            self.console.print("[red]TOOLS_DIR not set in Config[/red]")
            return tools

        try:
            for module_info in pkgutil.iter_modules([str(tools_path)]):
                if module_info.name in ["base", "text_processor", "text_analyzer"]:
                    continue

                try:
                    module = importlib.import_module(f"tools.{module_info.name}")
                    self._extract_tools_from_module(module, tools)
                except ImportError as import_err:
                    self.console.print(
                        f"[yellow]ImportError loading {module_info.name}: {import_err}[/yellow]"
                    )
                    continue
                except Exception as mod_err:
                    self.console.print(
                        f"[red]Error loading module {module_info.name}:[/red] {str(mod_err)}\n{mod_err.__class__.__name__}"
                    )
        except Exception as overall_err:
            self.console.print(
                f"[red]Error in tool loading process:[/red] {str(overall_err)}"
            )

        return tools

    def _extract_tools_from_module(self, module, tools: List[Dict[str, Any]]) -> None:
        """Extract and instantiate all tool classes from a module."""
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, BaseTool) and obj != BaseTool:
                try:
                    tool_instance = obj()
                    tools.append(tool_instance.to_dict())
                    self.console.print(
                        f"[green]Loaded tool:[/green] {tool_instance.name}"
                    )
                except Exception as tool_init_err:
                    self.console.print(
                        f"[red]Error initializing tool {name}:[/red] {str(tool_init_err)}"
                    )

    def _get_completion(self):
        """Get a completion from the Anthropic API with memory integration."""
        try:
            # Get relevant context from memory
            recent_messages = []
            for msg in self.conversation_history[-3:]:
                content = msg.get("content", "")
                if isinstance(content, list):
                    # Handle list of content blocks
                    text_content = []
                    for block in content:
                        if isinstance(block, dict) and "text" in block:
                            text_content.append(block["text"])
                        elif isinstance(block, str):
                            text_content.append(block)
                    content = " ".join(text_content)
                recent_messages.append(content)

            context_blocks = self.memory_manager.get_relevant_context(
                " ".join(recent_messages)
            )

            # Add context to system prompt
            context_text = "\n".join(block.content for block in context_blocks)
            system_prompt = f"{SystemPrompts.DEFAULT}\n\nContext:\n{context_text}\n\n{SystemPrompts.TOOL_USAGE}"

            # Prepare conversation history
            processed_history = []
            for msg in self.conversation_history:
                content = msg.get("content", "")
                # Skip tool result messages when sending to API
                if msg.get("role") == "tool_result":
                    continue
                if isinstance(content, list):
                    # Handle list of content blocks
                    text_content = []
                    for block in content:
                        if isinstance(block, dict) and "text" in block:
                            text_content.append(block["text"])
                        elif isinstance(block, str):
                            text_content.append(block)
                    processed_msg = {
                        "role": msg["role"],
                        "content": " ".join(text_content),
                    }
                else:
                    processed_msg = msg
                processed_history.append(processed_msg)

            response = self.client.messages.create(
                model=Config.MODEL,
                max_tokens=min(
                    Config.MAX_TOKENS,
                    Config.MAX_CONVERSATION_TOKENS - self.total_tokens_used,
                ),
                temperature=self.temperature,
                tools=self.tools,
                messages=processed_history,
                system=system_prompt,
            )

            # Update token usage
            if hasattr(response, "usage") and response.usage:
                message_tokens = (
                    response.usage.input_tokens + response.usage.output_tokens
                )
                self.total_tokens_used += message_tokens
                self._display_token_usage(response.usage)

            if self.total_tokens_used >= Config.MAX_CONVERSATION_TOKENS:
                self.console.print(
                    "\n[bold red]Token limit reached! Please reset the conversation.[/bold red]"
                )
                return "Token limit reached! Please type 'reset' to start a new conversation."

            if response.stop_reason == "tool_use":
                self.console.print(
                    "\n[bold yellow]  Handling Tool Use...[/bold yellow]\n"
                )

                tool_results = []
                if getattr(response, "content", None) and isinstance(
                    response.content, list
                ):
                    # Execute each tool in the response content
                    for content_block in response.content:
                        if content_block.type == "tool_use":
                            result = self._execute_tool(content_block)

                            # Handle structured data vs text
                            if isinstance(result, (list, dict)):
                                tool_results.append(
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": content_block.id,
                                        "content": result,
                                    }
                                )
                            else:
                                tool_results.append(
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": content_block.id,
                                        "content": [
                                            {"type": "text", "text": str(result)}
                                        ],
                                    }
                                )

                    # Add tool usage to conversation history with special role
                    self.conversation_history.append(
                        {"role": "assistant", "content": response.content}
                    )
                    self.conversation_history.append(
                        {"role": "tool_result", "content": tool_results}
                    )
                    return self._get_completion()

                else:
                    self.console.print(
                        "[red]No tool content received despite 'tool_use' stop reason.[/red]"
                    )
                    return "Error: No tool content received"

            # Final assistant response
            if (
                getattr(response, "content", None)
                and isinstance(response.content, list)
                and response.content
            ):
                final_content = response.content[0].text
                self.conversation_history.append(
                    {"role": "assistant", "content": final_content}
                )

                # Add memory block for assistant response
                self.memory_manager.add_memory_block(
                    content=final_content, significance_type=SignificanceType.LLM
                )

                return final_content
            else:
                self.console.print("[red]No content in final response.[/red]")
                return "No response content available."

        except Exception as e:
            logging.error(f"Error in _get_completion: {str(e)}")
            return f"Error: {str(e)}"

    def chat(self, user_input):
        """Process a chat message with memory integration."""
        if isinstance(user_input, str):
            if user_input.lower() == "refresh":
                self.refresh_tools()
                return "Tools refreshed successfully!"
            elif user_input.lower() == "reset":
                self.reset()
                return "Conversation reset!"
            elif user_input.lower() == "quit":
                return "Goodbye!"
            elif user_input.lower() == "memory":
                self._display_cli_stats(self.memory_manager.get_memory_stats())
                return "Memory stats displayed above."

        try:
            # Add to conversation history and memory
            self.conversation_history.append({"role": "user", "content": user_input})
            self.memory_manager.add_memory_block(
                content=user_input, significance_type=SignificanceType.USER
            )

            # Show thinking indicator if enabled
            if self.thinking_enabled:
                with Live(
                    Spinner("dots", text="Thinking...", style="cyan"),
                    refresh_per_second=10,
                    transient=True,
                ):
                    response = self._get_completion()
            else:
                response = self._get_completion()

            return response

        except Exception as e:
            logging.error(f"Error in chat: {str(e)}")
            return f"Error: {str(e)}"

    def reset(self):
        """Reset memory_manager, conversation history and stats."""
        self.memory_manager = MemoryManager(
            working_memory_limit=getattr(Config, "WORKING_MEMORY_LIMIT", 8192),
            archival_memory_limit=getattr(Config, "ARCHIVAL_MEMORY_LIMIT", 128000),
            archive_threshold=getattr(Config, "ARCHIVE_THRESHOLD", 6000),
            similarity_threshold=getattr(Config, "MEMORY_SIMILARITY_THRESHOLD", 0.85),
            cleanup_interval=getattr(Config, "MEMORY_CLEANUP_INTERVAL", 1000),
            memory_server_client=self.memory_client,
            stats_callback=self._broadcast_memory_stats,
        )
        self.last_recall_time = 0
        self.generation_count = 0
        self.promotion_count = 0
        self.demotion_count = 0
        self.merge_count = 0
        self.retrieval_count = 0
        self.conversation_history = []
        self.total_tokens_used = 0

        self.console.print(
            "\n[bold green]🔄 Assistant memory has been reset![/bold green]"
        )
        welcome_text = """
# Claude Engineer v3. A self-improving assistant framework with tool creation

Type 'refresh' to reload available tools
Type 'reset' to clear conversation history
Type 'memory' to view memory stats
Type 'quit' to exit

Available tools:
"""
        self.console.print(Markdown(welcome_text))
        self.display_available_tools()

def main():
    """Entry point for the assistant CLI loop."""
    console = Console()
    style = Style.from_dict({"prompt": "orange"})

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
Type 'memory' to view memory stats
Type 'quit' to exit

Available tools:
"""
    console.print(Markdown(welcome_text))
    assistant.display_available_tools()

    while True:
        try:
            user_input = prompt("You: ", style=style).strip()

            if user_input.lower() == "quit":
                console.print("\n[bold blue]👋 Goodbye![/bold blue]")
                break
            elif user_input.lower() == "reset":
                assistant.reset()
                continue

            response = assistant.chat(user_input)
            console.print("\n[bold purple]Claude Engineer:[/bold purple]")
            if isinstance(response, str):
                safe_response = response.replace("[", "\\[").replace("]", "\\]")
                console.print(safe_response)
            else:
                console.print(str(response))

        except KeyboardInterrupt:
            continue
        except EOFError:
            break

if __name__ == "__main__":
    main()
