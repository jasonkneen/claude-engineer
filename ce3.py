import asyncio
import importlib
import inspect
import json
import logging
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
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.text import Text

from config import Config

# Default spinner cleanup timeout in seconds (shorter for better CLI responsiveness)
SPINNER_CLEANUP_TIMEOUT = getattr(Config, 'SPINNER_CLEANUP_TIMEOUT', 2.0)
from prompts.system_prompts import SystemPrompts
from tools.base import BaseTool
from tools.contextmanager import ContextManager

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

        # Create logs directory if it doesn't exist
        self.logs_dir = "logs"
        os.makedirs(self.logs_dir, exist_ok=True)

    def _log_message(self, role: str, content: Any):
        """Log message to a file with timestamp, without duplicating tool output display"""
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
                                # Just log that a tool was used without repeating output
                                formatted_content += f"[Tool Use: {item.get('name')}]\n"
                            elif item.get('type') == 'tool_result':
                                # Skip tool results as they're already displayed
                                continue
                        else:
                            formatted_content += str(item) + '\n'
                else:
                    formatted_content = str(content)
                
                # Write the formatted log entry, skip if it's just tool output
                if formatted_content.strip():
                    f.write(f"[{timestamp}] {role}: {formatted_content.strip()}\n\n")
        except Exception as e:
            logging.error(f"Error writing to log file: {str(e)}")

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
        result_text = result['text'] if isinstance(result, dict) and 'text' in result else str(result)
        if "Error" not in result_text and "failed" not in result_text.lower():
            self.console.print("[green]The package was installed successfully.[/green]")
            return True
        else:
            self.console.print(f"[red]Failed to install {package_name}. Output:[/red] {result_text}")
            return False

    def _load_tools(self) -> List[Dict[str, Any]]:
        """
        Dynamically load all tool classes from the tools directory.
        If a dependency is missing, prompt the user to install it via uvpackagemanager.
        
        Returns:
            A list of tools (dicts) containing their 'name', 'description', and 'input_schema'.
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
            for module_info in pkgutil.iter_modules([str(tools_path)]):
                if module_info.name == 'base':
                    continue

                # Attempt loading the tool module
                try:
                    module = importlib.import_module(f'tools.{module_info.name}')
                    self._extract_tools_from_module(module, tools)
                except ImportError as e:
                    # Handle missing dependencies
                    missing_module = self._parse_missing_dependency(str(e))
                    self.console.print(f"\n[yellow]Missing dependency:[/yellow] {missing_module} for tool {module_info.name}")
                    user_response = input(f"Would you like to install {missing_module}? (y/n): ").lower()

                    if user_response == 'y':
                        success = self._execute_uv_install(missing_module)
                        if success:
                            # Retry loading the module after installation
                            try:
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

    def _display_tool_usage(self, tool_name: str, input_data: Dict, result: Union[str, Dict[str, Any]]):
        """
        If SHOW_TOOL_USAGE is enabled, display the input and result of a tool execution.
        Handles special cases like image data, large outputs, and serialized content for cleaner display.
        
        Args:
            tool_name: Name of the tool being used
            input_data: Dictionary of tool inputs
            result: Tool execution result, either as string or serialized dict
        """
        if not getattr(Config, 'SHOW_TOOL_USAGE', False):
            return

        # Clean up and serialize input data
        cleaned_input = self._clean_data_for_display(input_data)
        
        # Clean up and serialize result data, preserving formatting
        cleaned_result = self._clean_data_for_display(result)
        
        # Format tool info with plain text formatting
        tool_output = (
            f"╭── Tool used: {tool_name} ──╮\n"
            f"📥 Input: {json.dumps(cleaned_input.get('text', cleaned_input), indent=2)}\n"
            f"📤 Result: {cleaned_result.get('text', cleaned_result)}\n"
            f"╰{'─' * 30}╯"
        )
        self.console.print(tool_output)

    def _clean_data_for_display(self, data):
        """Clean data for display.
        
        A helper method that handles various data types and removes/replaces
        large content like base64 strings. Uses _serialize_chat_content for
        consistent serialization.
        """
        # If already properly serialized, just handle base64 content
        if isinstance(data, dict) and 'type' in data and 'text' in data:
            text = data['text']
            if isinstance(text, str) and len(text) > 1000 and ';base64,' in text:
                return {"type": "text", "text": "[base64 data omitted]"}
            return data
            
        # Otherwise serialize the content consistently
        serialized = self._serialize_chat_content(data)
        
        # Fallback to original cleaning method if serialization fails
        if isinstance(data, str):
            try:
                parsed_data = json.loads(data)
                cleaned = self._clean_parsed_data(parsed_data)
                return {"type": "text", "text": str(cleaned)}
            except json.JSONDecodeError:
                if len(data) > 1000 and ';base64,' in data:
                    return {"type": "text", "text": "[base64 data omitted]"}
                return {"type": "text", "text": data}
        elif isinstance(data, dict):
            cleaned = self._clean_parsed_data(data)
            return {"type": "text", "text": str(cleaned)}
        else:
            return {"type": "text", "text": str(data)}

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
        Handles both async and sync tool execution with proper timeout handling.
        """
        tool_name = tool_use.name
        tool_input = tool_use.input or {}
        tool_result = None

        try:
            module = importlib.import_module(f'tools.{tool_name}')
            tool_instance = self._find_tool_instance_in_module(module, tool_name)

            if not tool_instance:
                tool_result = {"type": "text", "text": f"Tool not found: {tool_name}"}
            else:
                # Execute the tool with the provided input and timeout handling
                try:
                    execute_method = getattr(tool_instance, 'execute')
                    
                    # Check if the execute method is async
                    if asyncio.iscoroutinefunction(execute_method):
                        try:
                            result = await asyncio.wait_for(
                                execute_method(**tool_input),
                                timeout=30.0  # 30 second timeout
                            )
                        except asyncio.TimeoutError:
                            logging.error(f"Tool execution timed out: {tool_name}")
                            return {"type": "text", "text": f"Error: Tool execution timed out after 30 seconds"}
                    else:
                        # For non-async tools, wrap in lambda to handle kwargs properly
                        loop = asyncio.get_event_loop()
                        try:
                            result = await asyncio.wait_for(
                                loop.run_in_executor(
                                    None,
                                    lambda: execute_method(**tool_input)
                                ),
                                timeout=30.0
                            )
                        except asyncio.TimeoutError:
                            logging.error(f"Tool execution timed out: {tool_name}")
                            return {"type": "text", "text": f"Error: Tool execution timed out after 30 seconds"}
                    
                    # Ensure result is properly serialized
                    tool_result = self._serialize_chat_content(result)
                except Exception as exec_err:
                    logging.error(f"Tool execution error: {str(exec_err)}", exc_info=True)
                    tool_result = {"type": "text", "text": f"Error executing tool '{tool_name}': {str(exec_err)}"}
        except ImportError:
            tool_result = {"type": "text", "text": f"Failed to import tool: {tool_name}"}
        except Exception as e:
            tool_result = {"type": "text", "text": f"Error executing tool: {str(e)}"}

        # Display tool usage with proper handling of structured data
        self._display_tool_usage(tool_name, tool_input, tool_result)
        # Return the result without duplicating the display
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
                            # Execute tool and get result (display is handled within _execute_tool)
                            result = await self._execute_tool(content_block)
                            
                            # Result is already serialized by _execute_tool
                            serialized_result = result

                            # Create the tool result with consistently formatted content
                            serialized_content = result  # Already properly serialized
                            if isinstance(serialized_content, dict) and 'text' in serialized_content:
                                tool_result = {
                                    "type": "tool_result",
                                    "tool_use_id": content_block.id,
                                    "content": [serialized_content]
                                }
                                tool_results.append(tool_result)

                    # First append the assistant's tool use request
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": response.content  # Keep original content with tool_use blocks
                    })
                    
                    # Then append tool results as user message (API requirement)
                    if tool_results:  # Only append if we have results
                        self.conversation_history.append({
                            "role": "user",
                            "content": tool_results  # Use already serialized tool_results
                        })
                    
                    # Properly await the recursive call
                    return await self._get_completion()

                else:
                    self.console.print("[red]No tool content received despite 'tool_use' stop reason.[/red]")
                    return "Error: No tool content received"

            # Final assistant response
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
                return final_content
            else:
                self.console.print("[red]No content in final response.[/red]")
                return "No response content available."

        except Exception as e:
            logging.error(f"Error in _get_completion: {str(e)}")
            return f"Error: {str(e)}"

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


    def _serialize_chat_content(self, content: Any) -> Dict[str, Any]:
        """
        Serialize content consistently, handling TextBlocks and other types.
        Always returns a Dict[str, Any] with 'type' and 'text' keys.
        """
        # Handle None or empty content
        if content is None:
            return {"type": "text", "text": ""}
            
        # If already properly formatted, return as is
        if isinstance(content, dict) and 'type' in content and 'text' in content:
            return content
            
        # Handle dictionaries first to prevent attribute access errors
        if isinstance(content, dict):
            if 'type' in content and 'text' in content:
                return content
            try:
                return {"type": "text", "text": json.dumps(content, indent=2)}
            except (TypeError, json.JSONDecodeError):
                return {"type": "text", "text": str(content)}

        # Handle any object that might have a text representation
        try:
            # Try to get plain text representation
            if hasattr(content, 'plain'):
                return {"type": "text", "text": content.plain}
            if hasattr(content, 'text'):
                return {"type": "text", "text": content.text}
            
            # Convert to string representation
            return {"type": "text", "text": str(content)}
        except Exception as e:
            # Log the error for debugging
            print(f"Error serializing content: {str(e)}")
            # Final fallback
            return {"type": "text", "text": str(content)}
            
        # Handle lists by recursively serializing items
        if isinstance(content, (list, tuple)):
            serialized_items = [self._serialize_chat_content(item) for item in content]
            # If all items are dicts with type/text, return them as a list
            if all(isinstance(item, dict) and 'type' in item and 'text' in item for item in serialized_items):
                return {"type": "text", "text": "\n".join(item['text'] for item in serialized_items)}
            return {"type": "text", "text": json.dumps(serialized_items, indent=2)}
            
        # Handle dictionaries
        if isinstance(content, dict):
            try:
                return {"type": "text", "text": json.dumps(content, indent=2)}
            except (TypeError, json.JSONDecodeError):
                return {"type": "text", "text": str(content)}
                
        # Handle everything else
        return {"type": "text", "text": str(content)}

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
                return "Goodbye!"

        try:
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
                        serialized_item = self._serialize_chat_content(item)
                        if serialized_item['text'].strip():  # Only add non-empty text
                            serialized_input.append(serialized_item)
                    except Exception as e:
                        logging.warning(f"Failed to serialize input item: {str(e)}")
                        # Convert problematic item to string representation
                        text = str(item)
                        if text.strip():
                            serialized_input.append({"type": "text", "text": text})
                            
                if not serialized_input:
                    return "Message cannot contain only empty or whitespace content"
            else:
                serialized_input = [self._serialize_chat_content(user_input)]

            # Debug: verify serialization
            try:
                json.dumps(serialized_input)
                logging.debug("Successfully serialized input: %s", json.dumps(serialized_input))
            except Exception as e:
                logging.error("Failed to serialize input: %s", str(e))

            # Add serialized user message to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": serialized_input
            })

            # Debug: verify conversation history
            try:
                json.dumps(self.conversation_history)
                logging.debug("Successfully serialized conversation history")
            except Exception as e:
                logging.error("Failed to serialize conversation history: %s", str(e))

            # Log user message
            self._log_message("user", serialized_input)

            # Show thinking indicator if enabled
            if self.thinking_enabled:
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
            else:
                response = await self._get_completion()

            # Ensure response is properly serialized
            if isinstance(response, str):
                serialized_response = self._serialize_chat_content(response)
            else:
                serialized_response = response  # Already serialized by _get_completion
                
            # Log assistant response
            self._log_message("assistant", serialized_response)

            # Ensure response is properly serialized for conversation history
            if isinstance(serialized_response, dict) and 'type' in serialized_response and 'text' in serialized_response:
                history_content = [serialized_response]
            else:
                # If somehow not properly serialized, create a proper format
                history_content = [{"type": "text", "text": str(serialized_response)}]
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": history_content
            })

            # Capture context after successful response
            await self._capture_conversation_context()
            
            return serialized_response.get('text', str(response))

        except Exception as e:
            logging.error(f"Error in chat: {str(e)}")
            return f"Error: {str(e)}"

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

    async def chat_loop():
        while True:
            try:
                # Use asyncio.shield to protect the prompt operation
                user_input = await asyncio.shield(session.prompt_async("You: "))
                user_input = user_input.strip()

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
                continue
            except EOFError:
                break
            except Exception as e:
                logging.error("Fatal error in chat loop:", exc_info=True)
                console.print(f"\n[bold red]Fatal Error:[/bold red] {str(e)}")
                break

    # Run the chat loop
    await chat_loop()


if __name__ == "__main__":
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
