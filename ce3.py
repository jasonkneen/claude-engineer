# ce3.py
import anthropic
import httpx
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from typing import List, Dict, Any, Optional
import importlib
import inspect
import pkgutil
import os
import json
import sys
import logging
import asyncio

from config import Config
from tools.base import BaseTool
from api_router import APIRouter, APIConfig
from tools.agent_manager import AgentManagerTool
from tools.test_agent import TestAgentTool
from tools.context_manager import ContextManagerTool
from tools.agent_base import AgentBaseTool, AgentRole
from prompt_toolkit import prompt
from prompt_toolkit.styles import Style
from prompts.system_prompts import SystemPrompts

# Configure logging to only show ERROR level and above
logging.basicConfig(
    level=logging.ERROR,
    format='%(levelname)s: %(message)s'
)

class Assistant:
    """
    The Assistant class manages:
    - Loading of tools from a specified directory.
    - Interaction with the Anthropics API (message completion).
    - Handling user commands such as 'refresh' and 'reset'.
    - Token usage tracking and display.
    - Tool execution upon request from model responses.
    """

    def __init__(self, config=None):
        """Initialize assistant with basic attributes."""
        self.config = config or Config
        self.test_mode = os.getenv('TEST_MODE', '').lower() == 'true'
        self.client = None
        self.api_router = None
        self.conversation_history = []
        self.console = Console()
        self.thinking_enabled = getattr(self.config, 'ENABLE_THINKING', False)
        self.temperature = getattr(self.config, 'DEFAULT_TEMPERATURE', 0.7)
        self.total_tokens_used = 0
        self.tools = []
        self.agent_manager = None
        self.logger = logging.getLogger(__name__)

    @classmethod
    async def create(cls, config=None):
        """Create and initialize a new assistant instance."""
        instance = cls(config)
        await instance.initialize()
        return instance

    async def initialize(self):
        """Initialize assistant components."""
        try:
            # Initialize API router only if not in test mode
            if not self.test_mode:
                # Initialize API router
                self.api_router = APIRouter()
                await self.api_router.setup()

                # Initialize Anthropic client
                if not getattr(Config, 'ANTHROPIC_API_KEY', None):
                    raise ValueError("No ANTHROPIC_API_KEY found in environment variables")

                # Create custom httpx client without problematic parameters
                http_client = httpx.Client(
                    base_url="https://api.anthropic.com",
                    timeout=60.0,
                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                )

                self.client = anthropic.Anthropic(
                    api_key=Config.ANTHROPIC_API_KEY,
                    http_client=http_client,
                    max_retries=3,
                    _strict_response_validation=True
                )

            # Initialize tools and agent manager
            self.tools = await self._load_tools()
            self.agent_manager = AgentManagerTool(name="manager")
            await self.agent_manager.initialize()

        except Exception as e:
            self.logger.error(f"Failed to initialize assistant: {str(e)}")
            raise

    def _execute_uv_install(self, package_name: str) -> bool:
        """
        Execute the uvpackagemanager tool directly to install the missing package.
        Returns True if installation seems successful (no errors in output), otherwise False.
        """
        class ToolUseMock:
            name = "uvpackagemanager"
            input = {
                "command": "install",
                "packages": [package_name]
            }

        result = self._execute_tool(ToolUseMock())
        if "Error" not in result and "failed" not in result.lower():
            self.console.print("[green]The package was installed successfully.[/green]")
            return True
        else:
            self.console.print(f"[red]Failed to install {package_name}. Output:[/red] {result}")
            return False

    async def _load_tools(self) -> List[BaseTool]:
        """
        Dynamically load all tool classes from the tools directory.
        If a dependency is missing, prompt the user to install it via uvpackagemanager.

        Returns:
            A list of BaseTool instances.
        """
        tools = []
        tools_path = getattr(Config, 'TOOLS_DIR', None)

        if tools_path is None:
            self.console.print("[red]TOOLS_DIR not set in Config[/red]")
            return tools

        # Clear cached tool modules for fresh import
        for module_name in list(sys.modules.keys()):
            if module_name.startswith('tools.') and module_name != 'tools.base':
                del sys.modules[module_name]

        try:
            # Load core agent tools first
            core_tools = [
                'agent_manager',
                'test_agent',
                'context_manager'
            ]
            for tool_name in core_tools:
                try:
                    module = importlib.import_module(f'tools.{tool_name}')
                    await self._extract_tools_from_module(module, tools)
                except ImportError as e:
                    self.console.print(f"[red]Failed to load core tool {tool_name}: {str(e)}[/red]")

            # Load additional tools
            for module_info in pkgutil.iter_modules([str(tools_path)]):
                if module_info.name == 'base' or module_info.name in core_tools:
                    continue

                try:
                    module = importlib.import_module(f'tools.{module_info.name}')
                    await self._extract_tools_from_module(module, tools)
                except ImportError as e:
                    missing_module = self._parse_missing_dependency(str(e))
                    self.console.print(f"\n[yellow]Missing dependency:[/yellow] {missing_module} for tool {module_info.name}")
                    user_response = input(f"Would you like to install {missing_module}? (y/n): ").lower()

                    if user_response == 'y':
                        success = self._execute_uv_install(missing_module)
                        if success:
                            try:
                                module = importlib.import_module(f'tools.{module_info.name}')
                                await self._extract_tools_from_module(module, tools)
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

    async def _extract_tools_from_module(self, module, tools: List[Any]) -> None:
        """
        Given a tool module, find and instantiate all tool classes (subclasses of BaseTool).
        Append the tool instances to the 'tools' list.
        """
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and issubclass(obj, BaseTool) and obj != BaseTool):
                try:
                    # Check if class is AgentBaseTool subclass
                    if issubclass(obj, AgentBaseTool):
                        # Generate unique agent ID and determine role
                        agent_id = f"{name.lower()}_{len(tools)}"
                        # Map tool name to role, fallback to CUSTOM
                        role_map = {
                            'TestAgentTool': AgentRole.TEST,
                            'ContextManagerTool': AgentRole.CONTEXT,
                            'AgentManagerTool': AgentRole.ORCHESTRATOR
                        }
                        role = role_map.get(name, AgentRole.CUSTOM)
                        tool_instance = obj(agent_id=agent_id, role=role)
                    else:
                        tool_instance = obj()

                    if hasattr(tool_instance, 'initialize'):
                        await tool_instance.initialize()

                    # Store the tool instance directly
                    tools.append(tool_instance)
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
        """Display available tools and their descriptions."""
        tool_names = []
        for tool in self.tools:
            # All tools are now BaseTool instances
            tool_names.append(tool.name)

        if tool_names:
            self.console.print("\nAvailable tools:")
            for name in sorted(tool_names):
                self._display_tool_usage(name)

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

        tool_info = f"""[cyan]📥 Input:[/cyan] {json.dumps(cleaned_input, indent=2)}
[cyan]📤 Result:[/cyan] {cleaned_result}"""
        
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

    async def _execute_tool(self, tool_use):
        """
        Given a tool usage request (with tool name and inputs),
        dynamically load and execute the corresponding tool.
        """
        tool_name = tool_use.name
        tool_input = tool_use.input or {}
        tool_result = None

        try:
            # Check if tool is an agent operation
            if tool_name in ['agent_manager', 'test_agent', 'context_manager']:
                tool_instance = getattr(self, tool_name, None)
                if tool_instance:
                    result = await tool_instance.execute(**tool_input)
                    tool_result = result
                else:
                    tool_result = f"Agent tool not initialized: {tool_name}"
            else:
                try:
                    module = importlib.import_module(f'tools.{tool_name}')
                    tool_instance = await self._find_tool_instance_in_module(module, tool_name)

                    if not tool_instance:
                        tool_result = f"Tool not found: {tool_name}"
                    else:
                        # Execute the tool with the provided input
                        try:
                            result = await tool_instance.execute(**tool_input)
                            # Keep structured data intact
                            tool_result = result
                        except Exception as exec_err:
                            tool_result = f"Error executing tool '{tool_name}': {str(exec_err)}"
                except ImportError:
                    tool_result = f"Failed to import tool: {tool_name}"
                except Exception as e:
                    logging.error(f"Error executing tool: {str(e)}")
                    tool_result = f"Error executing tool: {str(e)}"
        except Exception as e:
            tool_result = f"Error executing tool '{tool_name}': {str(e)}"
            logging.error(f"Error in _execute_tool: {str(e)}")

        # Display tool usage with proper handling of structured data
        self._display_tool_usage(tool_name, tool_input,
            json.dumps(tool_result) if not isinstance(tool_result, str) else tool_result)
        return tool_result

    async def _find_tool_instance_in_module(self, module, tool_name: str):
        """
        Search a given module for a tool class matching tool_name and return an instance of it.
        Handles both regular tools and agent-based tools with proper initialization.
        """
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and issubclass(obj, BaseTool) and obj != BaseTool):
                try:
                    if issubclass(obj, AgentBaseTool):
                        # Generate unique agent ID and determine role
                        agent_id = f"{name.lower()}_{tool_name}"
                        # Map tool name to role, fallback to CUSTOM
                        role_map = {
                            'TestAgentTool': AgentRole.TEST,
                            'ContextManagerTool': AgentRole.CONTEXT,
                            'AgentManagerTool': AgentRole.ORCHESTRATOR
                        }
                        role = role_map.get(name, AgentRole.CUSTOM)
                        candidate_tool = await obj(agent_id=agent_id, role=role)
                    else:
                        candidate_tool = await obj()

                    if candidate_tool.name == tool_name:
                        return candidate_tool
                except Exception as e:
                    self.console.print(f"[red]Error initializing tool {name}:[/red] {str(e)}")
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
        Get a completion using the API router.
        Handles both text-only and multimodal messages.
        """
        try:
            # Route request through API router
            response = await self.api_router.route_request(
                provider=Config.DEFAULT_PROVIDER,
                messages=self.conversation_history,
                config=APIConfig(
                    model=Config.MODEL,
                    max_tokens=min(
                        Config.MAX_TOKENS,
                        Config.MAX_CONVERSATION_TOKENS - self.total_tokens_used
                    ),
                    temperature=self.temperature,
                    tools=self.tools,
                    system=f"{SystemPrompts.DEFAULT}\n\n{SystemPrompts.TOOL_USAGE}"
                )
            )

            # Update token usage based on response usage
            if hasattr(response, 'usage') and response.usage:
                message_tokens = response.usage.input_tokens + response.usage.output_tokens
                self.total_tokens_used += message_tokens
                self._display_token_usage(response.usage)

            if self.total_tokens_used >= Config.MAX_CONVERSATION_TOKENS:
                self.console.print("\n[bold red]Token limit reached! Please reset the conversation.[/bold red]")
                return "Token limit reached! Please type 'reset' to start a new conversation."

            # Handle tool calls in the response content
            if hasattr(response, 'content') and isinstance(response.content, list):
                for content_block in response.content:
                    if hasattr(content_block, 'type') and content_block.type == 'tool_calls':
                        tool_results = []
                        for tool_call in content_block.tool_calls:
                            result = self._execute_tool(tool_call)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_call_id": tool_call.id,
                                "content": result
                            })

                        # Add tool results to conversation
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response.content
                        })
                        self.conversation_history.append({
                            "role": "user",
                            "content": tool_results
                        })
                        return await self._get_completion()

            # Handle final text response
            if hasattr(response, 'content') and isinstance(response.content, list):
                for content_block in response.content:
                    if hasattr(content_block, 'type') and content_block.type == 'text':
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response.content
                        })
                        return content_block.text

            self.console.print("[red]No valid content in response.[/red]")
            return "No response content available."

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

            # Handle final text response
            if hasattr(response, 'content') and isinstance(response.content, list):
                for content_block in response.content:
                    if hasattr(content_block, 'type') and content_block.type == 'text':
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response.content
                        })
                        return content_block.text

            self.console.print("[red]No valid content in response.[/red]")
            return "No response content available."

        except Exception as e:
            logging.error(f"Error in _get_completion: {str(e)}")  # P24a9
            return f"Error: {str(e)}"

    async def chat(self, user_input: str) -> str:
        """Process user input and return assistant response."""
        try:
            if user_input.lower() == 'reset':
                return self.reset()
            elif user_input.lower() == 'refresh':
                self.refresh_tools()
                return "Tools refreshed!"
            elif user_input.lower() == 'tools':
                self.display_available_tools()
                return "Tools displayed above."

            if self.test_mode:
                # Mock response for test mode
                if isinstance(user_input, str) and 'createfolderstool' in user_input.lower():
                    return "Test Mode: I would create a folder using createfolderstool, but I'm in test mode."
                return "Test Mode: This is a mock response. The application is working correctly, but API calls are disabled."

            # Add user message to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": [{"type": "text", "text": user_input}]
            })

            # Show thinking indicator if enabled
            if self.thinking_enabled:
                with Live(Spinner('dots', text='Thinking...', style="cyan"),
                         refresh_per_second=10, transient=True):
                    response = await self._get_completion()
            else:
                response = await self._get_completion()

            # Update conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })

            return response
        except Exception as e:
            self.console.print(f"[red]Error in chat:[/red] {str(e)}")
            return f"Error: {str(e)}"
    def reset(self):
        """
        Reset the assistant's memory and token usage.
        """
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
    """
    Entry point for the assistant CLI loop.
    Provides a prompt for user input and handles 'quit' and 'reset' commands.
    """
    console = Console()
    style = Style.from_dict({'prompt': 'orange'})

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
            user_input = prompt("You: ", style=style).strip()

            if user_input.lower() == 'quit':
                console.print("\n[bold blue]👋 Goodbye![/bold blue]")
                break
            elif user_input.lower() == 'reset':
                assistant.reset()
                continue

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
    import asyncio
    asyncio.run(main())

   

   

   

   

   

   

   

   

   

   

   

   

   

   

   

   

   

   

   