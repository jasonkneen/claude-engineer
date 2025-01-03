# ce3.py
from anthropic import AsyncAnthropic
import asyncio
import aiofiles
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from typing import List, Dict, Any, Optional, Tuple
import importlib
import inspect
import pkgutil
from dataclasses import dataclass
import os
import json
import sys
import logging

from config import Config
from tools.base import BaseTool 
from prompt_toolkit import prompt
from prompt_toolkit.styles import Style
from prompt_toolkit.application import run_in_terminal
from prompts.system_prompts import SystemPrompts

# Configure logging to only show ERROR level and above
logging.basicConfig(
    level=logging.ERROR,
    format='%(levelname)s: %(message)s'
)
@dataclass
class ContextSummary:
    key_points: List[str]
    decisions: List[str]
    important_context: str
    last_updated: str

class Memory:
    """Manages conversation history and context summaries"""
    def __init__(self):
        self.full_history: List[Dict[str, Any]] = []
        self.summary: Optional[ContextSummary] = None
        self.total_tokens: int = 0

    def add_exchange(self, role: str, content: Any):
        """Add a new message exchange to history"""
        self.full_history.append({
            "role": role,
            "content": content
        })
        if len(self.full_history) % 5 == 0:  # Update summary every 5 messages
            self._update_summary()

    def _update_summary(self):
        """Generate/update context summary from conversation history"""
        key_points = []
        decisions = []
        important_context = ""
        
        # Extract key information from history
        for msg in self.full_history[-10:]:  # Focus on recent history
            content = msg["content"]
            if isinstance(content, list):
                content = " ".join(c.text for c in content if hasattr(c, 'text'))
            elif not isinstance(content, str):
                content = str(content)
            
            # Identify key points (important statements)
            if any(marker in content.lower() for marker in ["important", "key", "critical", "must", "should"]):
                key_points.append(content.split(".")[-2] if "." in content else content)
            
            # Track decisions
            if any(marker in content.lower() for marker in ["decided", "agreed", "will", "plan"]):
                decisions.append(content)
        
        # Compile important context
        important_context = f"Based on the last {len(self.full_history)} messages: "
        important_context += " ".join(key_points[:3])  # Most recent key points
        
        self.summary = ContextSummary(
            key_points=key_points[-5:],  # Keep last 5 key points
            decisions=decisions[-3:],    # Keep last 3 decisions
            important_context=important_context,
            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

    async def save_context(self, filename_prefix: str = "context"):
        """Save both full history and summary"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save full history
        full_history_file = f"{filename_prefix}_full_{timestamp}.json"
        summary_file = f"{filename_prefix}_summary_{timestamp}.json"
        
        try:
            async with aiofiles.open(full_history_file, 'w') as f:
                await f.write(json.dumps({
                    'full_history': self.full_history,
                    'total_tokens': self.total_tokens
                }, indent=2))
            
            # Save summary if available
            if self.summary:
                async with aiofiles.open(summary_file, 'w') as f:
                    await f.write(json.dumps({
                        'summary': asdict(self.summary)
                    }, indent=2))
            
            return full_history_file, summary_file
        except Exception as e:
            logging.error(f"Error saving context: {str(e)}")
            return None, None

    def load_context(self, load_full: bool = False) -> bool:
        """Load context with option for full history"""
        try:
            latest_summary = self._find_latest_file("context_summary")
            if latest_summary:
                with open(latest_summary, 'r') as f:
                    data = json.load(f)
                    summary_dict = data.get('summary', {})
                    self.summary = ContextSummary(**summary_dict)
            
            if load_full:
                latest_full = self._find_latest_file("context_full")
                if latest_full:
                    with open(latest_full, 'r') as f:
                        data = json.load(f)
                        self.full_history = data.get('full_history', [])
                        self.total_tokens = data.get('total_tokens', 0)
            
            return True
        except Exception as e:
            logging.error(f"Error loading context: {str(e)}")
            return False

    def _find_latest_file(self, prefix: str) -> Optional[str]:
        """Find most recent context file with given prefix"""
        try:
            files = [f for f in os.listdir('.') if f.startswith(prefix) and f.endswith('.json')]
            return max(files, key=lambda x: os.path.getmtime(x)) if files else None
        except Exception:
            return None

    def get_current_context(self) -> str:
        """Get current context summary for conversation"""
        if not self.summary:
            return "No context available."
        
        return f"""
        Current Context:
        Last Updated: {self.summary.last_updated}
        
        Key Points:
        {chr(10).join(f'- {point}' for point in self.summary.key_points)}
        
        Recent Decisions:
        {chr(10).join(f'- {decision}' for decision in self.summary.decisions)}
        
        Summary: {self.summary.important_context}
        """

class Assistant:
    """
    The Assistant class manages:
    - Loading of tools from a specified directory.
    - Interaction with the Anthropics API (message completion).
    - Handling user commands such as 'refresh' and 'reset'.
    - Token usage tracking and display.
    - Tool execution upon request from model responses.
    """

    def __init__(self, auto_save_interval: int = 300, load_context: bool = True):  # Default 5 minutes
        if not getattr(Config, 'ANTHROPIC_API_KEY', None):
            raise ValueError("No ANTHROPIC_API_KEY found in environment variables")
        
        # Load saved context if enabled
        self.memory = Memory()
        if load_context:
            self.memory.load_context()

        # Initialize Anthropics client
        self.client = AsyncAnthropic(api_key=Config.ANTHROPIC_API_KEY)

        self.conversation_history: List[Dict[str, Any]] = []
        self.console = Console()

        self.thinking_enabled = getattr(Config, 'ENABLE_THINKING', False)
        self.temperature = getattr(Config, 'DEFAULT_TEMPERATURE', 0.7)
        self.total_tokens_used = 0

        self.tools = self._load_tools()

        # Auto-save settings
        self.auto_save_interval = auto_save_interval
        self.auto_save_task = None
            

    async def _auto_save_loop(self):
        """
        Background task that periodically saves the conversation context.
        """
        try:
            while True:
                await asyncio.sleep(self.auto_save_interval)
                await self.save_context()
        except asyncio.CancelledError:
            # Handle task cancellation gracefully
            pass

    async def save_context(self):
        """
        Saves both full conversation history and summary context to timestamped files.
        Uses the memory system to maintain both full history and summary information.
        """
        if not self.conversation_history:
            return

        full_file, summary_file = await self.memory.save_context()
        if full_file and summary_file:
            self.console.print(f"[green]Context saved to {full_file} and {summary_file}[/green]")

    def _execute_uv_install(self, package_name: str) -> bool:
        """
        Execute the uvpackagemanager tool directly to install the missing package.
        Returns True if installation seems successful (no errors in output), otherwise False.
        """
        class ToolUseMock:
            def __init__(self):
                self.name = "uvpackagemanager"
                self.input = {
                    "command": "install",
                    "packages": [package_name]
                }

        mock_tool = ToolUseMock()
        result = self._execute_tool(mock_tool)
        if "Error" not in result and "failed" not in result.lower():
            self.console.print("[green]The package was installed successfully.[/green]")
            return True
        else:
            self.console.print(f"[red]Failed to install {package_name}. Output:[/red] {result}")
            return False

    async def start_auto_save(self):
        """
        Initialize the auto-save task when the event loop is ready.
        Should be called after Assistant initialization when event loop is running.
        """
        if self.auto_save_interval > 0 and not self.auto_save_task:
            self.auto_save_task = asyncio.create_task(self._auto_save_loop())

    async def shutdown(self):
        """
        Cleanup method to be called when shutting down the assistant.
        Ensures auto-save task is properly cancelled and final context is saved.
        """
        if self.auto_save_task and not self.auto_save_task.done():
            self.auto_save_task.cancel()
            try:
                await self.auto_save_task
            except asyncio.CancelledError:
                pass
            finally:
                self.auto_save_task = None

        # Save final context before shutdown
        await self.save_context()

    def _find_latest_context_file(self) -> str:
        """
        Find the most recent context file in the current directory.
        Returns:
            str: Path to the most recent context file, or None if no context files found
        """
        try:
            context_files = [f for f in os.listdir('.') if f.startswith('context_') and f.endswith('.json')]
            if not context_files:
                return None
            return max(context_files, key=lambda x: os.path.getmtime(x))
        except Exception as e:
            self.console.print(f"[yellow]Warning: Error finding context files: {str(e)}[/yellow]")
            return None

    def _load_latest_context(self):
        """
        Load the most recent context file if available.
        """
        latest_context = self._find_latest_context_file()
        if not latest_context:
            return
        
        try:
            with open(latest_context, 'r') as f:
                data = json.load(f)
                self.conversation_history = data.get('conversation_history', [])
                self.total_tokens_used = data.get('total_tokens_used', 0)
            self.console.print(f"[green]Loaded context from {latest_context}[/green]")
        except Exception as e:
            self.console.print(f"[yellow]Warning: Failed to load context from {latest_context}: {str(e)}[/yellow]")
            # Initialize empty conversation history on failed load
            self.conversation_history = []
            self.total_tokens_used = 0

    def _load_tools(self) -> List[Dict[str, Any]]:
        """
        Dynamically load all tool classes from the tools directory.
        If a dependency is missing, prompt the user to install it via uvpackagemanager.
        Includes cycle detection and prevents recursive loading.
        
        Returns:
            A list of tools (dicts) containing their 'name', 'description', and 'input_schema'.
        """
        tools = []
        tools_path = getattr(Config, 'TOOLS_DIR', None)
        attempted_modules = set()  # Track modules we've tried to load
        installed_packages = set()  # Track packages we've tried to install

        if tools_path is None:
            self.console.print("[red]TOOLS_DIR not set in Config[/red]")
            return tools

        try:
            for module_info in pkgutil.iter_modules([str(tools_path)]):
                if module_info.name == 'base' or module_info.name in attempted_modules:
                    continue

                attempted_modules.add(module_info.name)

                # Attempt loading the tool module
                try:
                    module = importlib.import_module(f'tools.{module_info.name}')
                    self._extract_tools_from_module(module, tools)
                except ImportError as e:
                    # Handle missing dependencies
                    missing_module = self._parse_missing_dependency(str(e))
                    
                    # Check if we've already tried to install this package
                    if missing_module in installed_packages:
                        self.console.print(f"[yellow]Skipping {missing_module} - already attempted installation[/yellow]")
                        continue
                        
                    self.console.print(f"\n[yellow]Missing dependency:[/yellow] {missing_module} for tool {module_info.name}")
                    user_response = input(f"Would you like to install {missing_module}? (y/n): ").lower()

                    if user_response == 'y':
                        installed_packages.add(missing_module)  # Mark package as attempted
                        success = self._execute_uv_install(missing_module)
                        if success:
                            try:
                                # Only try to import the specific module once
                                module = importlib.import_module(f'tools.{module_info.name}')
                                self._extract_tools_from_module(module, tools)
                            except Exception as retry_err:
                                self.console.print(f"[red]Failed to load tool after installation: {str(retry_err)}[/red]")
                        else:
                            self.console.print(f"[red]Installation of {missing_module} failed. Skipping this tool.[/red]")
                    else:
                        self.console.print(f"[yellow]Skipping tool {module_info.name} due to missing dependency[/yellow]")
                except Exception as mod_err:
                    self.console.print(f"[red]Error loading module {module_info.name}:[/red] {str(mod_err)}")
        except Exception as overall_err:
            self.console.print(f"[red]Error in tool loading process:[/red] {str(overall_err)}")

        return tools

    def _parse_missing_dependency(self, error_str: str) -> str:
        """
        Parse the missing dependency name from an ImportError string.
        """
        if "No module named" in error_str:
            parts = error_str.split("No module named")
            missing_module = parts[-1].strip(" '\"")
        else:
            missing_module = error_str
        return missing_module

    def _extract_tools_from_module(self, module, tools: List[Dict[str, Any]]) -> None:
        """
        Given a tool module, find and instantiate all tool classes (subclasses of BaseTool).
        Append them to the 'tools' list.
        """
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
                except Exception as tool_init_err:
                    self.console.print(f"[red]Error initializing tool {name}:[/red] {str(tool_init_err)}")

    def refresh_tools(self):
        """
        Refresh the list of tools and show newly discovered tools.
        """
        current_tool_names = {tool['name'] for tool in self.tools}
        self.tools = self._load_tools()
        new_tool_names = {tool['name'] for tool in self.tools}
        new_tools = new_tool_names - current_tool_names

        if new_tools:
            self.console.print("\n")
            for tool_name in new_tools:
                tool_info = next((t for t in self.tools if t['name'] == tool_name), None)
                if tool_info:
                    description_lines = tool_info['description'].strip().split('\n')
                    formatted_description = '\n    '.join(line.strip() for line in description_lines)
                    self.console.print(f"[bold green]NEW[/bold green] 🔧 [cyan]{tool_name}[/cyan]:\n    {formatted_description}")
        else:
            self.console.print("\n[yellow]No new tools found[/yellow]")

    def display_available_tools(self):
        """
        Print a list of currently loaded tools.
        """
        self.console.print("\n[bold cyan]Available tools:[/bold cyan]")
        tool_names = [tool['name'] for tool in self.tools]
        if tool_names:
            formatted_tools = ", ".join([f"🔧 [cyan]{name}[/cyan]" for name in tool_names])
        else:
            formatted_tools = "No tools available."
        self.console.print(formatted_tools)
        self.console.print("\n---")

    def _display_tool_usage(self, tool_name: str, input_data: Dict, result: str):
        """
        If SHOW_TOOL_USAGE is enabled, display the input and result of a tool execution.
        Handles special cases like image data and large outputs for cleaner display.
        """
        if not getattr(Config, 'SHOW_TOOL_USAGE', False):
            return

        # Clean up input data by removing any large binary/base64 content
        cleaned_input = self._clean_data_for_display(input_data)
        
        # Clean up result data
        cleaned_result = self._clean_data_for_display(result)

        tool_info = f"""[cyan]\U0001F4E5 Input:[/cyan] {json.dumps(cleaned_input, indent=2)}
                [cyan]\U0001F4E4 Result:[/cyan] {cleaned_result}"""
        
        panel = Panel(
            tool_info,
            title=f"Tool used: {tool_name}",
            title_align="left",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(panel)

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
            return data

    def _clean_parsed_data(self, data):
        """
        Recursively clean parsed JSON/dict data, handling nested structures
        and replacing large data with placeholders.
        """
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                # Handle image data in various formats
                if key in ['data', 'image', 'source'] and isinstance(value, str):
                    if len(value) > 1000 and (';base64,' in value or value.startswith('data:')):
                        cleaned[key] = "[base64 data omitted]"
                    else:
                        cleaned[key] = value
                else:
                    cleaned[key] = self._clean_parsed_data(value)
            return cleaned
        elif isinstance(data, list):
            return [self._clean_parsed_data(item) for item in data]
        elif isinstance(data, str) and len(data) > 1000 and ';base64,' in data:
            return "[base64 data omitted]"
        return data

    def _execute_tool(self, tool_use):
        """
        Given a tool usage request (with tool name and inputs),
        dynamically load and execute the corresponding tool.
        """
        tool_name = tool_use.name
        tool_input = tool_use.input or {}
        tool_result = None

        try:
            module = importlib.import_module(f'tools.{tool_name}')
            tool_instance = self._find_tool_instance_in_module(module, tool_name)

            if not tool_instance:
                tool_result = f"Tool not found: {tool_name}"
            else:
                # Execute the tool with the provided input
                try:
                    result = tool_instance.execute(**tool_input)
                    # Keep structured data intact
                    tool_result = result
                except Exception as exec_err:
                    tool_result = f"Error executing tool '{tool_name}': {str(exec_err)}"
        except ImportError:
            tool_result = f"Failed to import tool: {tool_name}"
        except Exception as e:
            tool_result = f"Error executing tool: {str(e)}"

        # Display tool usage with proper handling of structured data
        self._display_tool_usage(tool_name, tool_input, 
            json.dumps(tool_result) if not isinstance(tool_result, str) else tool_result)
        return tool_result

    def _find_tool_instance_in_module(self, module, tool_name: str):
        """
        Search a given module for a tool class matching tool_name and return an instance of it.
        """
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and issubclass(obj, BaseTool) and obj != BaseTool):
                candidate_tool = obj()
                if candidate_tool.name == tool_name:
                    return candidate_tool
        return None

    def _display_token_usage(self, usage):
        """
        Display a visual representation of token usage and remaining tokens.
        Uses only the tracked total_tokens_used.
        """
        used_percentage = (self.total_tokens_used / Config.MAX_CONVERSATION_TOKENS) * 100
        remaining_tokens = max(0, Config.MAX_CONVERSATION_TOKENS - self.total_tokens_used)

        self.console.print(f"\nTotal used: {self.total_tokens_used:,} / {Config.MAX_CONVERSATION_TOKENS:,}")

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

    async def _get_completion(self):
        """
        Get a completion from the Anthropic API.
        Handles both text-only and multimodal messages.
        """
        while True:  # Use a loop instead of recursion
            try:
                response = await self.client.messages.create(
                    model=Config.MODEL,
                    max_tokens=min(
                        Config.MAX_TOKENS,
                        Config.MAX_CONVERSATION_TOKENS - self.total_tokens_used
                    ),
                    temperature=self.temperature,
                    tools=self.tools,
                    messages=self.conversation_history,
                    system=f"{SystemPrompts.DEFAULT}\n\n{SystemPrompts.TOOL_USAGE}"
                )

                # Update token usage based on response usage
                if hasattr(response, 'usage') and response.usage:
                    message_tokens = response.usage.input_tokens + response.usage.output_tokens
                    self.total_tokens_used += message_tokens
                    self._display_token_usage(response.usage)

                if self.total_tokens_used >= Config.MAX_CONVERSATION_TOKENS:
                    self.console.print("\n[bold red]Token limit reached! Please reset the conversation.[/bold red]")
                    return "Token limit reached! Please type 'reset' to start a new conversation."

                if response.stop_reason == "tool_use":
                    self.console.print("\n[bold yellow]  Handling Tool Use...[/bold yellow]\n")

                    tool_results = []
                    if getattr(response, 'content', None) and isinstance(response.content, list):
                        # Execute each tool in the response content
                        for content_block in response.content:
                            if content_block.type == "tool_use":
                                result = self._execute_tool(content_block)
                                
                                # Handle structured data (like image blocks) vs text
                                if isinstance(result, (list, dict)):
                                    tool_results.append({
                                        "type": "tool_result",
                                        "tool_use_id": content_block.id,
                                        "content": result  # Keep structured data intact
                                    })
                                else:
                                    # Convert text results to proper content blocks
                                    tool_results.append({
                                        "type": "tool_result",
                                        "tool_use_id": content_block.id,
                                        "content": [{"type": "text", "text": str(result)}]
                                    })

                        # Append tool usage to conversation and continue loop
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response.content
                        })
                        self.conversation_history.append({
                            "role": "user",
                            "content": tool_results
                        })
                        continue  # Continue the loop instead of recursive call

                    else:
                        self.console.print("[red]No tool content received despite 'tool_use' stop reason.[/red]")
                        return "Error: No tool content received"

                # Final assistant response
                if (getattr(response, 'content', None) and 
                    isinstance(response.content, list) and 
                    response.content):
                    final_content = response.content[0].text
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": response.content
                    })
                    return final_content
                else:
                    self.console.print("[red]No content in final response.[/red]")
                    return "No response content available."

            except Exception as e:
                logging.error(f"Error in _get_completion: {str(e)}")
                return f"Error: {str(e)}"

    async def chat(self, user_input):
        """
        Process a chat message from the user.
        user_input can be either a string (text-only) or a list (multimodal message)
        """
        # Handle special commands only for text-only messages
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
            # Add user message to memory and conversation history
            self.memory.add_exchange("user", user_input)
            self.conversation_history.append({
                "role": "user",
                "content": user_input if isinstance(user_input, str) else str(user_input)
            })

            # Get completion with or without thinking indicator
            if self.thinking_enabled:
                with Live(Spinner("dots", text="Thinking..."), refresh_per_second=8):
                    response = await self._get_completion()
            else:
                response = await self._get_completion()

            return response

        except Exception as e:
            logging.error(f"Error in chat: {str(e)}")
            return f"Error: {str(e)}"

    async def reset(self, load_previous: bool = False):
        """
        Reset the assistant's memory and token usage.
        Args:
            load_previous: If True, loads the most recent context after reset
        """
        # Cancel auto-save task if it exists
        if self.auto_save_task:
            self.auto_save_task.cancel()
            try:
                await self.auto_save_task
            except asyncio.CancelledError:
                pass
            
        self.conversation_history = []
        self.total_tokens_used = 0
        
        # Load previous context if requested
        if load_previous:
            self._load_latest_context()
        self.console.print("\n[bold green]\U0001F504 Assistant memory has been reset![/bold green]")

        welcome_text = """
        # Claude Engineer v3. A self-improving assistant framework with tool creation

        Type 'refresh' to reload available tools
        Type 'reset' to clear conversation history
        Type 'quit' to exit

        Available tools:
        """
        self.console.print(Markdown(welcome_text))
        self.display_available_tools()





async def async_init():
    """
    Initialize the assistant and its components asynchronously.
    Returns the initialized assistant or raises an error.
    """
    try:
        assistant = Assistant()
        await assistant.start_auto_save()
        return assistant
    except ValueError as e:
        raise ValueError(f"Initialization error: {str(e)}\nPlease ensure ANTHROPIC_API_KEY is set correctly.")

async def async_chat_loop(assistant, console, style):
    """
    Main chat loop handling user interactions asynchronously.
    """
    while True:
        try:
            # Run prompt in executor to avoid blocking
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, lambda: prompt("You: ", style=style).strip()
            )
            
            if user_input.lower() == 'quit':
                await assistant.shutdown()
                console.print("\n[bold blue]\U0001F44B Goodbye![/bold blue]")
                break
            elif user_input.lower() == 'reset':
                await assistant.reset()
                continue
            
            # Process other inputs
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
        except Exception as e:
            console.print(f"[red]Error:[/red] {str(e)}")
            continue

async def main():
    """
    Main entry point that coordinates initialization and the chat loop.
    """
    console = Console()
    style = Style.from_dict({'prompt': 'orange'})

    try:
        assistant = await async_init()
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
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

    await async_chat_loop(assistant, console, style)

def cli_entry():
    """
    Command-line entry point that sets up the event loop.
    """
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except Exception as e:
        print(f"Fatal error: {str(e)}")
    finally:
        loop.close()

if __name__ == "__main__":
    cli_entry()
