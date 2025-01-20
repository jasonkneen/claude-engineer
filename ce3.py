<<<<<<< HEAD
#!/usr/bin/env python3
import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from typing import List, Dict, Any
=======
import asyncio
>>>>>>> 901df3c2d2b2933ae1feaa3a96b01468b96f1696
import importlib
import inspect
import json
import logging
<<<<<<< HEAD
from prompt_toolkit import prompt
from prompt_toolkit.styles import Style

from config import Config
from tools.base import BaseTool
from prompts.system_prompts import SystemPrompts
from memory_manager import MemoryManager, MemoryBlock, SignificanceType, MemoryLevel
from memory_server_client import MemoryServerClient
=======
import os
import pkgutil
import platform
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import anthropic
import psutil
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner

from config import Config

# Default spinner cleanup timeout in seconds (shorter for better CLI responsiveness)
SPINNER_CLEANUP_TIMEOUT = getattr(Config, 'SPINNER_CLEANUP_TIMEOUT', 2.0)
from prompts.system_prompts import SystemPrompts
from tools.base import BaseTool
from tools.contextmanager import ContextManager
>>>>>>> 901df3c2d2b2933ae1feaa3a96b01468b96f1696

# Configure logging
logging.basicConfig(level=logging.ERROR, format="%(levelname)s: %(message)s")

class Assistant:
    def __init__(self):
<<<<<<< HEAD
        # Initialize console first
=======
        if not getattr(Config, 'ANTHROPIC_API_KEY', None):
            raise ValueError("No ANTHROPIC_API_KEY found in environment variables")

        # Initialize Anthropics async client for proper async support
        self.client = anthropic.AsyncAnthropic(api_key=Config.ANTHROPIC_API_KEY)

        self.conversation_history: List[Dict[str, Any]] = []
>>>>>>> 901df3c2d2b2933ae1feaa3a96b01468b96f1696
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
        # Initialize context manager
        self.context_manager = ContextManager()
        
        self.tools = self._load_tools()

        # Create logs directory if it doesn't exist
        self.logs_dir = "logs"
        os.makedirs(self.logs_dir, exist_ok=True)

    def _log_message(self, role: str, content: Any):
        """Log message to a file with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file = os.path.join(self.logs_dir, f"conversation_{datetime.now().strftime('%Y%m%d')}.log")
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                # Format the content based on its type
                if isinstance(content, list):
                    # Handle list of content blocks
                    formatted_content = ""
                    for item in content:
                        if isinstance(item, dict):
                            if item.get('type') == 'text':
                                formatted_content += item.get('text', '') + '\n'
                            elif item.get('type') == 'tool_use':
                                formatted_content += f"[Tool Use: {item.get('name')}]\n"
                        else:
                            formatted_content += str(item) + '\n'
                else:
                    formatted_content = str(content)
                
                # Write the formatted log entry
                f.write(f"[{timestamp}] {role}: {formatted_content.strip()}\n\n")
        except Exception as e:
            logging.error(f"Error writing to log file: {str(e)}")

    def __init__(self):
        if not getattr(Config, 'ANTHROPIC_API_KEY', None):
            raise ValueError("No ANTHROPIC_API_KEY found in environment variables")

        # Initialize Anthropics async client for proper async support
        self.client = anthropic.AsyncAnthropic(api_key=Config.ANTHROPIC_API_KEY)

        self.conversation_history: List[Dict[str, Any]] = []
        self.console = Console()

        self.thinking_enabled = getattr(Config, 'ENABLE_THINKING', False)
        self.temperature = getattr(Config, 'DEFAULT_TEMPERATURE', 0.7)
        self.total_tokens_used = 0

        # Initialize context manager
        self.context_manager = ContextManager()
        
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
        # self._display_cli_stats(stats)

    def _display_cli_stats(self, stats):
        """Display memory system statistics in CLI"""
        if not stats:
            return
    def _clean_data_for_display(self, data):
        """
        Helper method to clean data for display by handling various data types
        and removing/replacing large content like base64 strings.
        """
        if isinstance(data, str):
            try:
                # Try to parse as JSON first
                parsed_data = json.loads(data)
                return self._clean_parsed_data(parsed_data)
            except json.JSONDecodeError:
                # If it's a long string, check for base64 patterns
                if len(data) > 1000 and ';base64,' in data:
                    return "[base64 data omitted]"
                return data
        elif isinstance(data, dict):
            return self._clean_parsed_data(data)
        else:
            return str(data)

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

<<<<<<< HEAD
        # Nexus points section
        nexus = stats.get("nexus_points", {})
        nexus_text = [
            f"Total: {nexus.get('count', 0):,}",
            "Types: "
            + ", ".join(f"{k}: {v:,}" for k, v in nexus.get("types", {}).items()),
        ]
=======
            if not tool_instance:
                tool_result = f"Tool not found: {tool_name}"
            else:
                # Execute the tool with the provided input
                try:
                    result = tool_instance.execute(**tool_input)
                    # Keep structured data intact
                    tool_result = result
                except Exception as exec_err:
                    logging.error(f"Tool execution error: {str(exec_err)}", exc_info=True)
                    tool_result = f"Error executing tool '{tool_name}': {str(exec_err)}"
        except ImportError:
            tool_result = f"Failed to import tool: {tool_name}"
        except Exception as e:
            tool_result = f"Error executing tool: {str(e)}"
>>>>>>> 901df3c2d2b2933ae1feaa3a96b01468b96f1696

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

    def _execute_tool(self, tool_use):
        """Execute a tool with memory integration."""
        tool_name = tool_use.name
        tool_input = tool_use.input or {}
        tool_result = None

        try:
            module = importlib.import_module(f"tools.{tool_name}")
            tool_instance = self._find_tool_instance_in_module(module, tool_name)

            if not tool_instance:
                tool_result = f"Tool not found: {tool_name}"
            else:
                try:
                    result = tool_instance.execute(**tool_input)
                    tool_result = result

                    # Add memory block for successful tool execution
                    self.memory_manager.add_memory_block(
                        content=f"Tool execution: {tool_name} - {str(result)}",
                        significance_type=SignificanceType.SYSTEM,
                    )
                except Exception as exec_err:
                    tool_result = f"Error executing tool '{tool_name}': {str(exec_err)}"
        except ImportError:
            tool_result = f"Failed to import tool: {tool_name}"
        except Exception as e:
            tool_result = f"Error executing tool: {str(e)}"

        # Display tool usage
        self._display_tool_usage(tool_name, tool_input, tool_result)
        return tool_result

    def _find_tool_instance_in_module(self, module, tool_name: str):
        """Search a given module for a tool class matching tool_name and return an instance of it."""
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, BaseTool) and obj != BaseTool:
                candidate_tool = obj()
                if candidate_tool.name == tool_name:
                    return candidate_tool
        return None

    def _display_tool_usage(self, tool_name: str, input_data: Dict, result: Any):
        """Display tool usage with memory integration."""
        if not getattr(Config, "SHOW_TOOL_USAGE", False):
            return

        # Clean up data for display
        cleaned_input = self._clean_data_for_display(input_data)
        cleaned_result = self._clean_data_for_display(result)

        tool_info = f"""[cyan]📥 Input:[/cyan] {json.dumps(cleaned_input, indent=2)}
[cyan]📤 Result:[/cyan] {cleaned_result}"""

        panel = Panel(
            tool_info,
            title=f"Tool used: {tool_name}",
            title_align="left",
            border_style="cyan",
            padding=(1, 2),
        )
        self.console.print(panel)

    def _clean_data_for_display(self, data):
        """Clean data for display by handling various data types."""
        if isinstance(data, str):
            try:
                parsed_data = json.loads(data)
                return self._clean_parsed_data(parsed_data)
            except json.JSONDecodeError:
                if len(data) > 1000 and ";base64," in data:
                    return "[base64 data omitted]"
                return data
        elif isinstance(data, dict):
            return self._clean_parsed_data(data)
        else:
            return data

    def _clean_parsed_data(self, data):
        """Recursively clean parsed JSON/dict data."""
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                if key in ["data", "image", "source"] and isinstance(value, str):
                    if len(value) > 1000 and (
                        ";base64," in value or value.startswith("data:")
                    ):
                        cleaned[key] = "[base64 data omitted]"
                    else:
                        cleaned[key] = value
                else:
                    cleaned[key] = self._clean_parsed_data(value)
            return cleaned
        elif isinstance(data, list):
            return [self._clean_parsed_data(item) for item in data]
        elif isinstance(data, str) and len(data) > 1000 and ";base64," in data:
            return "[base64 data omitted]"
        return data

<<<<<<< HEAD
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
=======
    async def _get_completion(self) -> str:
        """
        Get a completion from the Anthropic API.
        Handles both text-only and multimodal messages.
        Returns:
            str: The response text or error message
        """
        try:
            # Use async client's create method
            response = await self.client.messages.create(
>>>>>>> 901df3c2d2b2933ae1feaa3a96b01468b96f1696
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
<<<<<<< HEAD
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": content_block.id,
                                    "content": result,
                                }
                            )

                    # Add tool usage to conversation history
                    self.conversation_history.append(
                        {"role": "assistant", "content": response.content}
                    )
                    if tool_results:  # Only add tool results if we have any
                        self.conversation_history.append(
                            {"role": "tool_result", "content": tool_results}
                        )
                        return self._get_completion()  # Continue the conversation
                    else:
                        return "No tool results available."  # Stop if no tool results
=======
                            
                            # Convert result to serializable format
                            def serialize_content(content):
                                """Recursively serialize content, handling TextBlocks consistently"""
                                if hasattr(content, 'text'):  # TextBlock
                                    return {"type": "text", "text": str(content.text)}
                                elif isinstance(content, dict):
                                    return {k: serialize_content(v) for k, v in content.items()}
                                elif isinstance(content, list):
                                    return [serialize_content(item) for item in content]
                                elif isinstance(content, str):
                                    return {"type": "text", "text": content}
                                else:
                                    try:
                                        # Try JSON serialization
                                        json.dumps(content)
                                        return content
                                    except (TypeError, json.JSONDecodeError):
                                        return {"type": "text", "text": str(content)}

                            serialized_result = serialize_content(result)

                            # Create the tool result with consistently formatted content
                            tool_result = {
                                "type": "tool_result",
                                "tool_use_id": content_block.id,
                            }

                            # Always wrap content in a list of objects
                            if isinstance(serialized_result, list):
                                # If it's already a list, ensure each item has type
                                tool_result["content"] = [
                                    {"type": "text", "text": str(item)} if not isinstance(item, dict) else item
                                    for item in serialized_result
                                ]
                            elif isinstance(serialized_result, dict):
                                # Single dict becomes a list with one item
                                tool_result["content"] = [serialized_result]
                            else:
                                # Any other type becomes a text object in a list
                                tool_result["content"] = [{"type": "text", "text": str(serialized_result)}]

                            tool_results.append(tool_result)

                    # Ensure tool results are properly serialized
                    serialized_tool_results = []
                    for result in tool_results:
                        if isinstance(result, dict):
                            try:
                                # Test JSON serialization
                                json.dumps(result)
                                serialized_tool_results.append(result)
                            except (TypeError, json.JSONDecodeError):
                                # Convert to simple text format if serialization fails
                                serialized_tool_results.append({
                                    "type": "text",
                                    "text": str(result)
                                })
                        else:
                            serialized_tool_results.append({
                                "type": "text",
                                "text": str(result)
                            })

                    # First append the assistant's tool use request
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": response.content  # Keep original content with tool_use blocks
                    })
                    
                    # Then append tool results as user message
                    if tool_results:  # Only append if we have results
                        self.conversation_history.append({
                            "role": "user",
                            "content": serialized_tool_results
                        })
                    
                    # Properly await the recursive call
                    return await self._get_completion()
>>>>>>> 901df3c2d2b2933ae1feaa3a96b01468b96f1696

                else:
                    self.console.print(
                        "[red]No tool content received despite 'tool_use' stop reason.[/red]"
                    )
                    return "Error: No tool content received"

            # Final assistant response
<<<<<<< HEAD
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

=======
            if (getattr(response, 'content', None) and 
                isinstance(response.content, list) and 
                response.content):
                # Ensure content is consistently formatted and serializable
                serializable_content = []
                for content_item in response.content:
                    if hasattr(content_item, 'type'):
                        if content_item.type == 'text':
                            # Ensure text content is properly formatted
                            serializable_content.append({
                                'type': 'text',
                                'text': str(content_item.text) if content_item.text else ""
                            })
                        elif content_item.type == 'tool_use':
                            # Ensure tool use content has all required fields
                            tool_use_content = {
                                'type': 'tool_use',
                                'id': content_item.id,
                                'name': content_item.name,
                            }
                            # Ensure input is a dictionary
                            if hasattr(content_item, 'input'):
                                tool_use_content['input'] = (
                                    content_item.input if isinstance(content_item.input, dict)
                                    else {'value': str(content_item.input)}
                                )
                            else:
                                tool_use_content['input'] = {}
                            serializable_content.append(tool_use_content)
                    else:
                        # Convert any untyped content to text type
                        text_content = str(content_item)
                        if text_content.strip():  # Only add non-empty content
                            serializable_content.append({
                                'type': 'text',
                                'text': text_content
                            })
                
                final_content = serializable_content[0]['text'] if serializable_content else "No response content available."
                self.conversation_history.append({
                    "role": "assistant",
                    "content": serializable_content
                })
>>>>>>> 901df3c2d2b2933ae1feaa3a96b01468b96f1696
                return final_content
            else:
                self.console.print("[red]No content in final response.[/red]")
                return "No response content available."

        except Exception as e:
            logging.error(f"Error in _get_completion: {str(e)}")
            return f"Error: {str(e)}"

<<<<<<< HEAD
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
=======
    async def _capture_conversation_context(self):
        """
        Capture and summarize the current conversation context.
        """
        if not self.conversation_history:
            return

        # Convert conversation history to a structured format for context
        context_data = json.dumps(self.conversation_history, indent=2)

        # Capture and summarize context
        await self.context_manager.capture_context(context_data)

    def get_latest_context_summary(self) -> Optional[Dict]:
        """
        Retrieve the most recent context summary.
        """
        return self.context_manager.get_latest_context(include_full=False)

    def get_all_context_summaries(self, include_archived: bool = False) -> List[Dict]:
        """
        Retrieve all available context summaries.
        """
        return self.context_manager.get_all_summaries(include_archived=include_archived)

    async def _show_thinking_spinner(self):
        """
        Async context manager for showing thinking spinner.
        """
        spinner = Spinner('dots', text='Thinking...', style="cyan")
        with Live(spinner, refresh_per_second=10, transient=True) as live:
            try:
                while True:
                    await asyncio.sleep(0.1)
                    live.refresh()
            except asyncio.CancelledError:
                pass


    async def chat(self, user_input: Union[str, List[Any]]) -> str:
        """
        Process a chat message from the user.
        user_input can be either a string (text-only) or a list (multimodal message)
        
        Args:
            user_input: The input message from the user
            
        Returns:
            str: The response message
            
        Raises:
            ValueError: If the input is empty or contains only whitespace
        """
        # Validate input is not empty or whitespace
        if isinstance(user_input, str):
            if not user_input.strip():
                return "Message cannot be empty or contain only whitespace"
            
            # Handle special commands
            cmd = user_input.lower()
            if cmd == 'refresh':
                self.refresh_tools()
                return "Tools refreshed successfully!"
            elif cmd == 'reset':
                await self.reset()
                return "Conversation reset!"
            elif cmd == 'quit':
>>>>>>> 901df3c2d2b2933ae1feaa3a96b01468b96f1696
                return "Goodbye!"
            elif user_input.lower() == "memory":
                self._display_cli_stats(self.memory_manager.get_memory_stats())
                return "Memory stats displayed above."

        try:
<<<<<<< HEAD
            # Add to conversation history and memory
            self.conversation_history.append({"role": "user", "content": user_input})
            self.memory_manager.add_memory_block(
                content=user_input, significance_type=SignificanceType.USER
            )
=======
            # Ensure user input is properly serialized and validated
            if isinstance(user_input, str):
                # Validate string content
                if not user_input.strip():
                    return "Message cannot be empty or contain only whitespace"
                serialized_input = [{"type": "text", "text": user_input}]
            elif isinstance(user_input, list):
                if not user_input:
                    return "Message list cannot be empty"
                    
                serialized_input = []
                for item in user_input:
                    try:
                        if hasattr(item, 'text'):  # Handle TextBlock objects
                            text = str(item.text) if item.text else ""
                            if text.strip():  # Only add non-empty text
                                serialized_input.append({"type": "text", "text": text})
                        elif hasattr(item, '__dict__'):  # Handle custom objects
                            # Convert object attributes to dict and ensure JSON serializable
                            obj_dict = {k: str(v) for k, v in item.__dict__.items()}
                            serialized_input.append({"type": "text", "text": str(obj_dict)})
                        elif isinstance(item, dict):
                            # Ensure the dict is JSON serializable by converting all values to strings
                            serialized_dict = {k: str(v) for k, v in item.items()}
                            serialized_input.append(serialized_dict)
                        else:
                            # Convert any other type to string representation
                            text = str(item)
                            if text.strip():  # Only add non-empty text
                                serialized_input.append({"type": "text", "text": text})
                    except (TypeError, json.JSONDecodeError, AttributeError) as e:
                        logging.warning(f"Failed to serialize input item: {str(e)}")
                        # Convert problematic item to string representation
                        text = str(item)
                        if text.strip():
                            serialized_input.append({"type": "text", "text": text})
                            
                if not serialized_input:
                    return "Message cannot contain only empty or whitespace content"
            else:
                serialized_input = [{"type": "text", "text": str(user_input)}]

            # Add serialized user message to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": serialized_input
            })
>>>>>>> 901df3c2d2b2933ae1feaa3a96b01468b96f1696

            # Log user message
            self._log_message("user", serialized_input)

            # Show thinking indicator if enabled
            if self.thinking_enabled:
<<<<<<< HEAD
                with Live(
                    Spinner("dots", text="Thinking...", style="cyan"),
                    refresh_per_second=10,
                    transient=True,
                ):
                    response = self._get_completion()
=======
                spinner_task = asyncio.create_task(self._show_thinking_spinner())
                try:
                    response = await self._get_completion()
                finally:
                    spinner_task.cancel()
                    try:
                        await asyncio.wait_for(spinner_task, timeout=SPINNER_CLEANUP_TIMEOUT)
                    except asyncio.CancelledError:
                        pass
                    except asyncio.TimeoutError:
                        mem = psutil.virtual_memory()
                        cpu_percent = psutil.cpu_percent(interval=0.1)
                        logging.warning(
                            f"Spinner task cleanup timed out after {SPINNER_CLEANUP_TIMEOUT}s. "
                            f"System info: CPU: {cpu_percent}%, Memory: {mem.percent}% used, "
                            f"Platform: {platform.system()} {platform.release()}"
                        )
                    except Exception as e:
                        logging.error(f"Error cleaning up spinner task: {str(e)}", exc_info=True)
>>>>>>> 901df3c2d2b2933ae1feaa3a96b01468b96f1696
            else:
                response = await self._get_completion()

            # Log assistant response
            self._log_message("assistant", response)

            # Capture context after successful response
            await self._capture_conversation_context()
            
            return response

        except Exception as e:
            logging.error(f"Error in chat: {str(e)}")
            return f"Error: {str(e)}"

<<<<<<< HEAD
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
=======
    async def reset(self):
        """
        Reset the assistant's memory and token usage.
        Ensures proper cleanup of conversation context before resetting.
        
        This is an async operation because it needs to capture the final context
        before clearing the conversation history.
        
        The reset operation includes:
        1. Capturing final context if there's conversation history
        2. Clearing conversation history
        3. Resetting token usage counter
        
        Returns:
            None
            
        Raises:
            asyncio.TimeoutError: If context capture times out
            Exception: For other errors during reset
        """
        try:
            # Capture final context before reset if there's conversation history
            if self.conversation_history:
                try:
                    # Use a shorter timeout for context capture
                    await asyncio.wait_for(
                        self._capture_conversation_context(),
                        timeout=min(SPINNER_CLEANUP_TIMEOUT, 1.0)  # Use shorter timeout for better responsiveness
                    )
                except asyncio.TimeoutError:
                    # Get system info for better error context
                    mem = psutil.virtual_memory()
                    cpu_percent = psutil.cpu_percent(interval=0.1)
                    logging.warning(
                        f"Context capture timed out during reset. "
                        f"System info: CPU: {cpu_percent}%, Memory: {mem.percent}% used"
                    )
                except Exception as e:
                    logging.error(
                        f"Error capturing final context during reset: {str(e)}",
                        exc_info=True
                    )
            
            # Clear conversation history and reset token usage
            self.conversation_history = []
            self.total_tokens_used = 0
            self.console.print("\n[bold green]🔄 Assistant memory has been reset![/bold green]")
        except Exception as e:
            error_msg = f"Critical error during reset operation: {str(e)}"
            logging.error(error_msg, exc_info=True)
            self.console.print(f"\n[bold red]Error:[/bold red] {error_msg}")
            raise  # Re-raise to ensure caller knows about the failure
>>>>>>> 901df3c2d2b2933ae1feaa3a96b01468b96f1696

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

<<<<<<< HEAD
def main():
    """Entry point for the assistant CLI loop."""
    console = Console()
    style = Style.from_dict({"prompt": "orange"})
=======

async def main():
    """
    Entry point for the assistant CLI loop.
    Provides a prompt for user input and handles 'quit' and 'reset' commands.
    """
    console = Console()
    style = Style.from_dict({'prompt': 'orange'})
    session = PromptSession(style=style)
>>>>>>> 901df3c2d2b2933ae1feaa3a96b01468b96f1696

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

    async def chat_loop():
        while True:
            try:
                # Use asyncio.shield to protect the prompt operation
                user_input = await asyncio.shield(session.prompt_async("You: "))
                user_input = user_input.strip()

<<<<<<< HEAD
            if user_input.lower() == "quit":
                console.print("\n[bold blue]👋 Goodbye![/bold blue]")
                break
            elif user_input.lower() == "reset":
                assistant.reset()
=======
                if user_input.lower() == 'quit':
                    console.print("\n[bold blue]\U0001F44B Goodbye![/bold blue]")
                    break
                elif user_input.lower() == 'reset':
                    await asyncio.shield(assistant.reset())
                    continue

                try:
                    # Shield the chat operation to prevent cancellation during processing
                    response = await asyncio.shield(assistant.chat(user_input))
                except anthropic.APIConnectionError as conn_error:
                    console.print(f"\n[bold red]Connection Error:[/bold red] {str(conn_error)}")
                    continue
                except anthropic.RateLimitError as rate_error:
                    console.print(f"\n[bold red]Rate Limit Error:[/bold red] {str(rate_error)}")
                    continue
                except anthropic.APIError as api_error:
                    console.print(f"\n[bold red]API Error:[/bold red] {str(api_error)}")
                    continue
                except asyncio.TimeoutError:
                    console.print("\n[bold red]Request timed out[/bold red]")
                    continue
                except Exception as chat_error:
                    logging.error("Chat error:", exc_info=True)
                    console.print(f"\n[bold red]Unexpected Error:[/bold red] {str(chat_error)}")
                    continue
                console.print("\n[bold purple]Claude Engineer:[/bold purple]")
                if isinstance(response, str):
                    safe_response = response.replace('[', '\[').replace(']', '\]')
                    console.print(safe_response)
                else:
                    console.print(str(response))

            except KeyboardInterrupt:
>>>>>>> 901df3c2d2b2933ae1feaa3a96b01468b96f1696
                continue
            except EOFError:
                break
            except Exception as e:
                logging.error("Fatal error in chat loop:", exc_info=True)
                console.print(f"\n[bold red]Fatal Error:[/bold red] {str(e)}")
                break

<<<<<<< HEAD
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
=======
    # Run the chat loop
    await chat_loop()
>>>>>>> 901df3c2d2b2933ae1feaa3a96b01468b96f1696

if __name__ == "__main__":
<<<<<<< HEAD
    main()
=======
    try:
        # Create new event loop and set as default
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the main coroutine
        try:
            loop.run_until_complete(main())
        finally:
            # Ensure proper cleanup
            loop.close()
    except Exception as e:
        logging.error(f"Error in main execution: {str(e)}", exc_info=True)
        raise
>>>>>>> 901df3c2d2b2933ae1feaa3a96b01468b96f1696
