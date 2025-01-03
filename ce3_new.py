from datetime import datetime
from anthropic import AsyncAnthropic
from dataclasses import asdict, dataclass, field
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

@dataclass
class ContextSummary:
    """Maintains the context and summary information for conversations
    
    Attributes:
        key_points: List of important points from the conversation
        decisions: List of decisions made during the conversation  
        important_context: String containing essential context
        last_updated: Timestamp of last update
    """
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

class PromptCache:
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
        
class Memory:
    """Manages conversation history and context summaries"""
    def __init__(self):
        self.full_history: List[Dict[str, Any]] = []
        self.summary: Optional[ContextSummary] = ContextSummary(
            key_points=[],
            decisions=[],
            important_context="No context available",
            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
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
        """Generate/update context summary from conversation history
        
        Analyzes recent conversation history to:
        - Extract key points and decisions
        - Maintain important context
        - Update the summary timestamp
        """
        try:
            key_points = []
            decisions = []
            important_context = ""
            
            # Extract key information from history
            for msg in self.full_history[-10:]:  # Focus on recent history
                if not isinstance(msg, dict) or "content" not in msg:
                    continue
                    
                content = msg["content"]
                # Handle different content types
                if isinstance(content, list):
                    # For structured content, extract text elements
                    text_parts = []
                    for item in content:
                        if hasattr(item, 'text'):
                            text_parts.append(item.text)
                        elif isinstance(item, dict) and 'text' in item:
                            text_parts.append(item['text'])
                    content = " ".join(text_parts)
                elif not isinstance(content, str):
                    content = str(content)
                
                if not content.strip():
                    continue
                    
                # Identify key points (important statements)
                if any(marker in content.lower() for marker in ["important", "key", "critical", "must", "should"]):
                    point = content.split(".")[-2].strip() if "." in content else content.strip()
                    if point and len(point) > 5:  # Basic validation
                        key_points.append(point)
                
                # Track decisions
                if any(marker in content.lower() for marker in ["decided", "agreed", "will", "plan"]):
                    if len(content) > 5:  # Basic validation
                        decisions.append(content.strip())
            
            # Compile important context
            important_context = f"Based on the last {len(self.full_history)} messages: "
            if key_points:
                important_context += " ".join(key_points[:3])  # Most recent key points
            else:
                important_context += "No key points identified."
            
            # Ensure we have valid lists even if empty
            key_points = key_points[-5:] if key_points else []  # Keep last 5 key points
            decisions = decisions[-3:] if decisions else []      # Keep last 3 decisions
            
            self.summary = ContextSummary(
                key_points=key_points,
                decisions=decisions,
                important_context=important_context,
                last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
        except Exception as e:
            logging.error(f"Error updating summary: {str(e)}")
            # Create a minimal valid summary on error
            self.summary = ContextSummary(
                key_points=[],
                decisions=[],
                important_context="Error occurred while generating summary",
                last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

    async def save_context(self, filename_prefix: str = "context"):
        """
        Save both full history and summary.
        Full history goes to contexts/ directory with timestamp,
        Summary goes to context_baton.json.
        Returns tuple of (full_history_file, context_baton_file) on success,
        or (None, None) on failure.
        """
        try:
            if not self.full_history:
                logging.info("No history to save")
                return (None, None)
            
            # Initialize summary if needed
            if not self.summary:
                self.summary = ContextSummary()
            # Always ensure we have a valid summary before saving
            if not self.summary:
                logging.info("Creating new summary before saving")
                self.summary = ContextSummary()
            
        # Ensure summary is up to date
        self._update_summary()
        if not self.summary:
            self.summary = ContextSummary(
                key_points=[],
                decisions=[],
                important_context="No context available",
                last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

        # Ensure summary is up to date before saving
        self._update_summary()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        full_history_file = None
        context_baton_file = 'context_baton.json'
        
        try:
            # Save full history to contexts directory
            os.makedirs('contexts', exist_ok=True)
            full_history_file = f"contexts/{filename_prefix}_{timestamp}.json"
            
            async with aiofiles.open(full_history_file, 'w') as f:
                await f.write(json.dumps({
                    'timestamp': timestamp,
                    'full_history': self.full_history,
                    'total_tokens': self.total_tokens
                }, indent=2))
            logging.info(f"Saved full history to {full_history_file}")
            
            # Save only summary to context_baton.json
            if self.summary and hasattr(self.summary, '__dataclass_fields__'):
                async with aiofiles.open(context_baton_file, 'w') as f:
                    await f.write(json.dumps({
                        'last_session': timestamp,
                        'summary': asdict(self.summary)
                    }, indent=2))
                logging.info(f"Saved context summary to {context_baton_file}")
                return full_history_file, context_baton_file
            else:
                logging.warning("No valid summary available to save to context baton")
                return full_history_file, None
                
        except Exception as e:
            logging.error(f"Error saving context: {str(e)}")
            return None, None

    def load_context(self, load_full: bool = False) -> bool:
        """
        Load context from storage.
        Always loads summary from context_baton.json,
        Optionally loads full history from contexts directory
        """
        try:
            # Load summary from context_baton.json 
            if os.path.exists('context_baton.json'):
                try:
                    with open('context_baton.json', 'r') as f:
                        data = json.load(f)
                        if data and 'summary' in data:
                            summary_dict = data.get('summary', {})
                            try:
                                self.summary = ContextSummary(**summary_dict) if summary_dict else None
                            except (TypeError, ValueError) as e:
                                logging.error(f"Error creating ContextSummary: {e}")
                                self.summary = None
                            last_session = data.get('last_session')
                        else:
                            logging.warning("No valid summary data found in context_baton.json")
                            last_session = None
                except json.JSONDecodeError as e:
                    logging.error(f"Error reading context_baton.json: {e}")
                    self.summary = None
                    last_session = None
            
            if load_full and last_session:
                context_file = f"contexts/context_{last_session}.json"
                if os.path.exists(context_file):
                    with open(context_file, 'r') as f:
                        data = json.load(f)
                        self.full_history = data.get('full_history', [])
                        self.total_tokens = data.get('total_tokens', 0)
            
            return True
        except Exception as e:
            logging.error(f"Error loading context: {str(e)}")
            return False

    def list_context_files(self) -> List[Dict[str, str]]:
        """
        List all available context files in the contexts directory
        Returns list of dicts with timestamp and filename
        """
        try:
            os.makedirs('contexts', exist_ok=True)
            files = [f for f in os.listdir('contexts') if f.startswith('context_') and f.endswith('.json')]
            return [{
                'timestamp': f.split('_')[1].split('.')[0],
                'filename': f,
                'path': os.path.join('contexts', f)
            } for f in sorted(files, reverse=True)]
        except Exception as e:
            logging.error(f"Error listing context files: {str(e)}")
            return []

    def _find_latest_file(self) -> Optional[str]:
        """Find most recent context file in contexts directory"""
        try:
            contexts = self.list_context_files()
            return contexts[0]['path'] if contexts else None
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
        
        # Initialize cache
        self.cache = PromptCache()
        
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
        self.console.print(f"Cache hits: {self.cache.hits} / Cache misses: {self.cache.misses}")
        if self.cache.hits + self.cache.misses > 0:
            hit_rate = (self.cache.hits / (self.cache.hits + self.cache.misses)) * 100
            self.console.print(f"Cache hit rate: {hit_rate:.1f}%")

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
                # Check cache first
                cached_response = self.cache.get(
                    self.conversation_history,
                    self.tools, 
                    self.temperature,
                    f"{SystemPrompts.DEFAULT}\n\n{SystemPrompts.TOOL_USAGE}"
                )
                if cached_response:
                    # Use cached response but still update token metrics
                    if hasattr(cached_response, 'usage') and cached_response.usage:
                        message_tokens = cached_response.usage.input_tokens + cached_response.usage.output_tokens
                        self.total_tokens_used += message_tokens
                        self._display_token_usage(cached_response.usage)
                    return cached_response
                
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

    async def reset(self, load_previous: bool = True):
        """
        Reset the assistant's memory and token usage.
        First saves the current context in the context baton, then loads just the summary on reset.
        Args:
            load_previous: If True, loads only the summary from previous context (default True)
        """
        logging.info("Starting assistant reset process")
        preserved_summary = None
        
        # Only attempt to save if we have conversation history
        if self.conversation_history:
            try:
                logging.info("Updating memory summary before saving context")
                # Force update summary before saving
                self.memory._update_summary()
                # Preserve current summary
                if self.memory.summary:
                    preserved_summary = ContextSummary(
                        key_points=self.memory.summary.key_points.copy(),
                        decisions=self.memory.summary.decisions.copy(),
                        important_context=self.memory.summary.important_context,
                        last_updated=self.memory.summary.last_updated
                    )
                    logging.info(f"Preserved current summary from {preserved_summary.last_updated}")
                
                # Attempt to save context
                save_result = await self.save_context()
                if save_result is not None:
                    full_file, baton_file = save_result
                    # Log success but differentiate between full and partial saves
                    if full_file and baton_file:
                        logging.info(f"Context fully saved to {full_file} and {baton_file}")
                        self.console.print(f"\n[green]Context fully saved to {full_file} and {baton_file}[/green]")
                    elif full_file:
                        logging.info(f"Only full history saved to {full_file}")
                        self.console.print(f"\n[yellow]Only full history saved to {full_file}[/yellow]")
                    else:
                        logging.warning("Failed to save context files")
                        self.console.print("[yellow]Failed to save context files[/yellow]")
                else:
                    logging.info("No context saved - save_context returned None")
                    self.console.print("[yellow]No context to save before reset[/yellow]")
            except Exception as e:
                logging.error(f"Error saving context during reset: {str(e)}")
                self.console.print("[red]Error saving context before reset[/red]")

        # Cancel auto-save task if running
        if self.auto_save_task and not self.auto_save_task.done():
            logging.info("Cancelling auto-save task")
            self.auto_save_task.cancel()
            try:
                await self.auto_save_task
            except asyncio.CancelledError:
                logging.info("Auto-save task cancelled successfully")
                pass

        # Clear current state while preserving summary if needed
        logging.info("Clearing current conversation state")
        self.conversation_history = []
        self.total_tokens_used = 0
        
        if load_previous:
            logging.info("Attempting to load previous context")
            # First try to load from context files
            success = self.memory.load_context(load_full=False)
            
            if success and self.memory.summary:
                logging.info("Successfully loaded context from baton")
                # Initialize conversation with loaded summary
                self.conversation_history.append({
                    "role": "system",
                    "content": self.memory.get_current_context()
                })
                self.console.print("[green]Previous context summary restored and initialized[/green]")
                self.console.print("[cyan]Context continuity maintained with previous session[/cyan]")
            elif preserved_summary:
                logging.info("Using preserved summary as fallback")
                self.memory.summary = preserved_summary
                self.conversation_history.append({
                    "role": "system",
                    "content": self.memory.get_current_context()
                })
                self.console.print("[yellow]Using preserved context summary[/yellow]")
            else:
                logging.warning("No previous context found to restore")
                self.console.print("[yellow]No previous context found to restore[/yellow]")
                # Initialize fresh summary
                self.memory.summary = ContextSummary()
        else:
            logging.info("Skipping previous context load as requested")
            self.memory.summary = ContextSummary()
        
        self.console.print("\n[bold green]\U0001F504 Assistant memory has been reset![/bold green]")
        logging.info("Reset process completed successfully")

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
