#!/usr/bin/env python3
# ce3 combined from ce3_OLD and ce3 (2d changes), with correct indentation and no syntax errors

# Standard Library
import io
import json
import logging
import os
import re
import sys
import importlib
import pkgutil
import inspect

# Third-Party Libraries
import anthropic
import psutil
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.spinner import Spinner
from rich.table import Table
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Type

# Local Imports
from config import Config
from ce3events import CE3EventHandler
from log_colors import ColorFormatter
from prompt_toolkit import prompt
from prompt_toolkit.styles import Style
from prompts.system_prompts import SystemPrompts
from tools.base import BaseTool

# Configure stdout encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HELP_TEXT = """
# CE3 Help

## Commands
- refresh : reload tools
- reset   : clear conversation
- quit    : exit
- help    : this help text

## Tool Chains
Use 'use X then Y' or 'chain X to Y' to chain tools.
"""

# Define role constants used in conversation
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"


@dataclass
class ToolChainStep:
    tool: Any
    args: Dict[str, Any]
    next_step: Optional["ToolChainStep"] = None


class ToolChainManager:
    """Manages dynamic tool chaining and execution"""

    def __init__(self):
        self.tools = {}
        self._chain_patterns = [
            (r"use (?:tool )?(.+?) then (.+)", self._parse_sequence),
            (r"chain (?:tool )?(.+?) to (.+)", self._parse_sequence),
            (r"after using (.+?) use (.+)", self._parse_sequence),
        ]

    def register_tool(self, tool_instance):
        """Register a tool with the chain manager"""
        self.tools[tool_instance.name] = tool_instance

    def parse_chain_command(self, command: str) -> Optional[ToolChainStep]:
        """Parse natural language command into tool chain"""
        for pattern, parser in self._chain_patterns:
            match = re.match(pattern, command, re.IGNORECASE)
            if match:
                return parser(*match.groups())
        return None

    def _parse_sequence(self, first_tool, remaining) -> Optional[ToolChainStep]:
        """Parse a sequence of tool commands"""
        items = [first_tool] + [x.strip() for x in remaining.split("then")]
        chain = None
        current = None
        for tool_name in items:
            if tool_name in self.tools:
                step = ToolChainStep(self.tools[tool_name], {})
                if chain is None:
                    chain = step
                    current = step
                else:
                    current.next_step = step
                    current = step
        return chain

    def execute_chain(self, initial_context: Dict) -> Dict:
        """Execute a chain of tools"""
        context = initial_context
        current_step = initial_context.get("_chain")
        while current_step:
            if hasattr(current_step.tool, "pre_completion"):
                context = current_step.tool.pre_completion(context)
            current_step = current_step.next_step
        return context


# Logging
log_level = logging.DEBUG if Config.DEBUG_MODE else logging.INFO
logging.basicConfig(level=log_level, format="%(message)s")
logging.getLogger().handlers[0].setFormatter(ColorFormatter())


class Assistant:
    """
    The Assistant class manages:
    - Loading of tools from a specified directory.
    - Interaction with the Anthropics API (message completion).
    - Handling user commands such as 'refresh' and 'reset'.
    - Token usage tracking and display.
    - Tool execution upon request from model responses.
    """

    def __init__(self):
        if not getattr(Config, 'ANTHROPIC_API_KEY', None):
            raise ValueError("No ANTHROPIC_API_KEY found in environment variables")

        # Initialize Anthropics client
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

        self.conversation_history: List[Dict[str, Any]] = []
        self.console = Console()

        self.thinking_enabled = getattr(Config, 'ENABLE_THINKING', False)
        self.temperature = getattr(Config, 'DEFAULT_TEMPERATURE', 0.7)
        self.total_tokens_used = 0

        # tools, interceptors, chain manager
        self.tools = []  # self._load_tools()
        self.interceptors = []  # self._load_interceptors()
        self.tool_chain_manager = ToolChainManager()

        # process monitor
        self.process = psutil.Process(os.getpid())

        # register all tools
        for tool in self.tools:
            self.tool_chain_manager.register_tool(tool)

        # event handler
        self.event_handler = CE3EventHandler()

    def _load_interceptors(self) -> List[Any]:
        """Load context interceptors from tools dir"""
        interceptors = []
        tools_dir = os.getenv(
            "CE3_TOOLS_DIR", os.path.join(os.path.dirname(__file__), "tools")
        )
        for _, name, _ in pkgutil.iter_modules([tools_dir]):
            try:
                module = importlib.import_module(f"tools.{name}")
                for _, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and hasattr(obj, "intercept_context"):
                        interceptors.append(obj())
            except ImportError as e:
                logging.error(f"Import error loading interceptor {name}: {str(e)}")
            except AttributeError as e:
                logging.error(f"Attribute error in interceptor {name}: {str(e)}")
            except Exception as e:
                logging.error(f"Unexpected error loading interceptor {name}: {str(e)}")
        return interceptors

    def _load_tools(self) -> List[BaseTool]:
        """Load all tool classes from tools dir, handle missing deps"""
        tools = []
        tools_path = os.path.join(os.path.dirname(__file__), "tools")

        if tools_path is None:
            self.console.print("[red]TOOLS_DIR not set in Config[/red]")
            return tools

        # Clear cached tool modules for fresh import
        for module_name in list(sys.modules.keys()):
            if module_name.startswith("tools.") and module_name != "tools.base":
                del sys.modules[module_name]

        for mod_info in pkgutil.iter_modules([str(tools_path)]):
            if mod_info.name == "base":
                continue
            try:
                module = importlib.import_module(f"tools.{mod_info.name}")
                self._extract_tools_from_module(module, tools)
            except ImportError as e:
                missing = self._parse_missing_dependency(str(e))
                self.console.print(
                    f"\n[yellow]Missing dependency:[/yellow] {missing} for tool {mod_info.name}"
                )
                answer = input(f"Install {missing}? (y/n): ").lower()
                if answer == "y":
                    if self._execute_uv_install(missing):
                        # retry
                        try:
                            module = importlib.import_module(f"tools.{mod_info.name}")
                            self._extract_tools_from_module(module, tools)
                        except Exception as re2:
                            self.console.print(
                                f"[red]Failed after install: {str(re2)}[/red]"
                            )
                    else:
                        self.console.print(f"[red]Install of {missing} failed[/red]")
                else:
                    self.console.print(f"[yellow]Skipping {mod_info.name}[/yellow]")
            except Exception as exc:
                self.console.print(
                    f"[red]Error loading module {mod_info.name}: {str(exc)}[/red]"
                )
        return tools

    def _parse_missing_dependency(self, err: str) -> str:
        if "No module named" in err:
            parts = err.split("No module named")
            return parts[-1].strip(" '\"")
        else:
            return err

    def _execute_uv_install(self, package: str) -> bool:
        """Directly call uvpackagemanager to install package"""

        class MockUse:
            name = "uvpackagemanager"
            input = {"command": "install", "packages": [package]}

        result = self._execute_tool(MockUse())
        if "Error" not in result and "failed" not in result.lower():
            self.console.print("[green]Installed successfully[/green]")
            return True
        else:
            self.console.print("[red]Installation failed[/red]")
            return False

    def _extract_tools_from_module(self, module, tool_list: List[BaseTool]) -> None:
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, BaseTool) and obj != BaseTool:
                try:
                    instance = obj()
                    existing = [t.name for t in tool_list]
                    if instance.name in existing:
                        duplicates = sum(1 for x in existing if x == instance.name)
                        new_n = f"{instance.name}_{duplicates+1}"
                        logging.warning(
                            f"Duplicate tool name '{instance.name}' found, renaming to '{new_n}'"
                        )
                        instance.name = new_n
                    tool_list.append(instance)
                    self.console.print(f"[green]Loaded tool:[/green] {instance.name}")
                except Exception as e:
                    self.console.print(f"[red]Error init tool {name}: {str(e)}[/red]")

    def refresh_tools(self):
        current_names = {t.name for t in self.tools}
        self.tools = self._load_tools()
        new_names = {t.name for t in self.tools} - current_names
        if new_names:
            self.console.print("\n")
            for n in new_names:
                found = next((t for t in self.tools if t.name == n), None)
                if found and hasattr(found, "description"):
                    desc = found.description.strip().split("\n")
                    form = "\n    ".join(x.strip() for x in desc)
                    self.console.print(
                        f"[bold green]NEW[/bold green] 🔧 [cyan]{n}[/cyan]:\n    {form}"
                    )
                else:
                    self.console.print(
                        f"[bold green]NEW[/bold green] 🔧 [cyan]{n}[/cyan]"
                    )
        else:
            self.console.print("\n[yellow]No new tools found[/yellow]")

    def display_available_tools(self):
        self.console.print("\n[bold cyan]Available tools:[/bold cyan]")
        names = [t.name for t in self.tools]
        if names:
            self.console.print(", ".join([f"🔧 [cyan]{nm}[/cyan]" for nm in names]))
        else:
            self.console.print("No tools available.")
        self.console.print("\n---")

    def _execute_tool(self, use):
        """Dynamically load + run a tool"""
        tname = use.name
        tinput = use.input or {}
        result = None
        try:
            mod = importlib.import_module(f"tools.{tname}")
            instance = self._find_tool_instance_in_module(mod, tname)
            if not instance:
                result = f"Tool not found: {tname}"
            else:
                try:
                    r = instance.execute(**tinput)
                    result = r
                except Exception as ex:
                    result = f"Error executing tool '{tname}': {str(ex)}"
        except ImportError:
            result = f"Failed to import tool: {tname}"
        except Exception as e:
            result = f"Error executing tool: {str(e)}"

        # show usage
        self._display_tool_usage(
            tname, tinput, json.dumps(result) if not isinstance(result, str) else result
        )
        return result

    def _find_tool_instance_in_module(self, module, tname: str):
        for nm, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, BaseTool) and obj != BaseTool:
                i = obj()
                if i.name == tname:
                    return i
        return None

    def _display_tool_usage(self, name: str, inp: Dict, result: str):
        if not getattr(Config, "SHOW_TOOL_USAGE", False):
            return
        ci = self._clean_data_for_display(inp)
        cr = self._clean_data_for_display(result)
        content = (
            f"[cyan]📥 Input:[/cyan] {json.dumps(ci, indent=2)}\n"
            f"[cyan]📤 Result:[/cyan] {cr}"
        )
        panel = Panel(
            content, title=f"Tool used: {name}", border_style="cyan", padding=(1, 2)
        )
        self.console.print(panel)

    def _clean_data_for_display(self, data):
        if isinstance(data, str):
            try:
                parse = json.loads(data)
                return self._clean_parsed_data(parse)
            except:
                if len(data) > 1000 and ";base64," in data:
                    return "[base64 data omitted]"
                return data
        elif isinstance(data, dict):
            return self._clean_parsed_data(data)
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

    def _get_completion(self):
        """
        Get a completion from the Anthropic API.
        Handles both text-only and multimodal messages.
        """
        try:
            # build context
            context = {
                "conversation_history": self.conversation_history,
                "total_tokens_used": self.total_tokens_used,
                "tools": self.tools,
            }
            for interceptor in self.interceptors:
                if hasattr(interceptor, "pre_completion"):
                    try:
                        context = interceptor.pre_completion(context)
                    except ValueError as e:
                        logging.error(
                            f"Value error in {interceptor.__class__.__name__}: {str(e)}"
                        )
                    except TypeError as e:
                        logging.error(
                            f"Type error in {interceptor.__class__.__name__}: {str(e)}"
                        )
                    except Exception as e:  # Fallback for unexpected errors
                        logging.error(
                            f"Unexpected error in {interceptor.__class__.__name__}: {str(e)}"
                        )

            # event processing
            processed = self.event_handler.process_context(context)
            self.conversation_history = processed["conversation_history"]
            self.total_tokens_used = processed["total_tokens_used"]

            """  if not self.conversation_history:
                self.conversation_history.append(
                    {
                        "role": ROLE_USER,
                        "content": [{"type": "text", "text": "Hello"}],
                    }
                ) """

            response = self.client.messages.create(
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
                        # Safely get type and id using getattr for object-style or get for dict-style
                        block_type = (
                            getattr(content_block, "type", None)
                            if hasattr(content_block, "type")
                            else content_block.get("type")
                        )
                        block_id = (
                            getattr(content_block, "id", None)
                            if hasattr(content_block, "id")
                            else content_block.get("id")
                        )

                        if block_type == "tool_use":
                            result = self._execute_tool(content_block)

                            # Handle structured data (like image blocks) vs text
                            if isinstance(result, (list, dict)):
                                tool_results.append(
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": block_id,
                                        "content": result,  # Keep structured data intact
                                    }
                                )
                            else:
                                # Convert text results to proper content blocks
                                tool_results.append(
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": block_id,
                                        "content": [
                                            {"type": "text", "text": str(result)}
                                        ],
                                    }
                                )

                    # Append tool usage to conversation and continue
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": response.content
                    })
                    self.conversation_history.append({
                        "role": "user",
                        "content": tool_results
                    })
                    return self._get_completion()  # Recursive call to continue the conversation

                else:
                    self.console.print("[red]No tool content received despite 'tool_use' stop reason.[/red]")
                    return "Error: No tool content received"

            # Final assistant response
            if (
                getattr(response, "content", None)
                and isinstance(response.content, list)
                and response.content
            ):
                # Safely get text from the first content block
                first_block = response.content[0]
                final_content = (
                    getattr(first_block, "text", None)
                    if hasattr(first_block, "text")
                    else first_block.get("text", "")
                )

                if final_content:
                    self.conversation_history.append(
                        {"role": "assistant", "content": response.content}
                    )
                    return final_content
                else:
                    self.console.print(
                        "[red]Could not extract text from response content.[/red]"
                    )
                    return "Error: Could not extract response text"
            else:
                self.console.print("[red]No content in final response.[/red]")
                return "No response content available."

        except Exception as e:
            logging.error(f"Error in _get_completion: {str(e)}")
            return f"Error: {str(e)}"

    def chat(self, user_input):
        """
        Process a chat message from the user.
        user_input can be either a string (text-only) or a list (multimodal message)
        """
        # Handle special commands only for text-only messages
        if isinstance(user_input, str):
            cmd = user_input.lower()
            if cmd == "refresh":
                self.refresh_tools()
                return None  # Command handled, no panel needed
            elif cmd == "reset":
                self.reset()
                return None  # Command handled, no panel needed
            elif cmd == "quit":
                return "Goodbye!"
            elif cmd == "help":
                return HELP_TEXT

        try:

            # Check for chain commands
            chain = self.tool_chain_manager.parse_chain_command(user_input)

            if chain:
                ctx = {
                    "conversation_history": self.conversation_history,
                    "total_tokens_used": self.total_tokens_used,
                    "tools": self.tools,
                    "_chain": chain,
                }
                ctx = self.tool_chain_manager.execute_chain(ctx)
                self.conversation_history = ctx["conversation_history"]
                self.total_tokens_used = ctx["total_tokens_used"]

                self.conversation_history.append(
                    {
                        "role": ROLE_USER,
                        "content": [{"type": "text", "text": user_input}],
                    }
                )

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

            # If not a chain command, just treat as normal user input
            self.conversation_history.append(
                {"role": ROLE_USER, "content": [{"type": "text", "text": user_input}]}
            )
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
        """
        Reset the assistant's memory and token usage.
        """
        self.conversation_history = []
        self.total_tokens_used = 0
        self.console.print(
            Panel(
                "[green]Assistant memory has been reset.[/green]\n"
                + "[cyan]Conversation history cleared.[/cyan]\n"
                + f"[yellow]Available tools: {len(self.tools)}[/yellow]",
                title="🔄 Reset Complete",
                border_style="green",
            )
        )
        welcome_text = """
# Claude Engineer v3. A self-improving assistant framework with tool creation

Type 'refresh' to reload available tools
Type 'reset' to clear conversation history
Type 'quit' to exit

Available tools:
"""
        self.console.print(Markdown(welcome_text))
        self.display_available_tools()


def main():
    """
    Entry point for the assistant CLI loop.
    Provides a prompt for user input and handles 'quit' and 'reset' commands.
    """
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
            elif user_input.lower() == "help":
                console.print(Panel(Markdown(HELP_TEXT), title="Help"))
                continue
            elif user_input.lower() == "refresh":
                assistant.refresh_tools()
                console.print("Tools refreshed!")
                continue

            response = assistant.chat(user_input)
            console.print("\n[bold purple]Claude Engineer:[/bold purple]")
            if isinstance(response, str):
                safe_response = response.replace("[", "\\[").replace("]", "\\]")
                console.print(
                    Panel.fit(
                        safe_response, title="🤖 Claude Engineer", border_style="blue"
                    )
                )
            else:
                console.print(str(response))
        except KeyboardInterrupt:
            continue
        except EOFError:
            break


if __name__ == "__main__":
    main()
