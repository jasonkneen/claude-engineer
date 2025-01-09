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
            print("The package was installed successfully.")
            return True
        else:
            print(f"Failed to install {package_name}. Output: {result_text}")
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
            print("Error: TOOLS_DIR not set in Config")
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
                    print(f"\nMissing dependency: {missing_module} for tool {module_info.name}")
                    user_response = input(f"Would you like to install {missing_module}? (y/n): ").lower()

                    if user_response == 'y':
                        success = self._execute_uv_install(missing_module)
                        if success:
                            # Retry loading the module after installation
                            try:
                                module = importlib.import_module(f'tools.{module_info.name}')
                                self._extract_tools_from_module(module, tools)
                            except Exception as retry_err:
                                print(f"Failed to load tool after installation: {str(retry_err)}")
                        else:
                            print(f"Installation of {missing_module} failed. Skipping this tool.")
                    else:
                        print(f"Skipping tool {module_info.name} due to missing dependency")
                except Exception as mod_err:
                    print(f"Error loading module {module_info.name}: {str(mod_err)}")
        except Exception as overall_err:
            print(f"Error in tool loading process: {str(overall_err)}")

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
                    print(f"Loaded tool: {tool_instance.name}")
                except Exception as tool_init_err:
                    print(f"Error initializing tool {name}: {str(tool_init_err)}")

    def refresh_tools(self):
        """
        Refresh the list of tools and show newly discovered tools.
        """
        current_tool_names = {tool['name'] for tool in self.tools}
        self.tools = self._load_tools()
        new_tool_names = {tool['name'] for tool in self.tools}
        new_tools = new_tool_names - current_tool_names

        if new_tools:
            print("\n")
            for tool_name in new_tools:
                tool_info = next((t for t in self.tools if t['name'] == tool_name), None)
                if tool_info:
                    description_lines = tool_info['description'].strip().split('\n')
                    formatted_description = '\n    '.join(line.strip() for line in description_lines)
                    print(f"NEW 🔧 {tool_name}:\n    {formatted_description}")
        else:
            print("\nNo new tools found")

    def display_available_tools(self):
        """
        Print a list of currently loaded tools.
        """
        print("\nAvailable tools:")
        tool_names = [tool['name'] for tool in self.tools]
        if tool_names:
            formatted_tools = ", ".join([f"🔧 {name}" for name in tool_names])
        else:
            formatted_tools = "No tools available."
        print(formatted_tools)
        print("\n---")

    def _display_tool_usage(self, tool_name: str, input_data: Any, result: Union[str, Dict[str, Any]]):
        """
        If SHOW_TOOL_USAGE is enabled, display the input and result of a tool execution.
        Handles special cases like image data, large outputs, and serialized content for cleaner display.
        
        Args:
            tool_name: Name of the tool being used
            input_data: Tool inputs (can be dict, string, or other types)
            result: Tool execution result, either as string or serialized dict
        """
        if not getattr(Config, 'SHOW_TOOL_USAGE', False):
            return

        # Convert input_data to dict if it's not already
        if not isinstance(input_data, dict):
            input_data = {"input": str(input_data)}

        # Clean up and serialize input data
        cleaned_input = self._clean_data_for_display(input_data)
        
        # Clean up and serialize result data, preserving formatting
        cleaned_result = self._clean_data_for_display(result)
        
        # Format tool info with plain text formatting
        tool_output = (
            f"=== Tool used: {tool_name} ===\n"
            f"Input: {json.dumps(cleaned_input.get('text', cleaned_input), indent=2)}\n"
            f"Result: {cleaned_result.get('text', cleaned_result)}\n"
            f"{'=' * 30}"
        )
        print(tool_output)

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

        # Convert any TextBlock objects in tool input
        def convert_input(obj):
            if hasattr(obj, '__class__') and obj.__class__.__name__ == 'TextBlock':
                return str(obj.text) if hasattr(obj, 'text') else str(obj)
            if isinstance(obj, dict):
                return {k: convert_input(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [convert_input(item) for item in obj]
            return obj
        
        tool_input = convert_input(tool_input)

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
                    
                    # Convert any TextBlock objects in the result immediately
                    def convert_result(obj):
                        if hasattr(obj, '__class__') and obj.__class__.__name__ == 'TextBlock':
                            return str(obj.text) if hasattr(obj, 'text') else str(obj)
                        if isinstance(obj, dict):
                            return {k: convert_result(v) for k, v in obj.items()}
                        if isinstance(obj, (list, tuple)):
                            return [convert_result(item) for item in obj]
                        if hasattr(obj, '__rich__'):
                            from rich.console import Console
                            console = Console(record=True, force_terminal=True)
                            console.print(obj)
                            return console.export_text(styles=True).strip()
                        return obj

                    # Convert result before serialization
                    converted_result = convert_result(result)
                    
                    # Always use _serialize_chat_content for consistent serialization
                    tool_result = self._serialize_chat_content(converted_result)
                    
                    # Verify the result is properly formatted
                    if not isinstance(tool_result, dict) or 'type' not in tool_result or 'text' not in tool_result:
                        logging.error("Tool result not properly formatted after serialization")
                        tool_result = {"type": "text", "text": str(converted_result)}
                    
                    # Double-check JSON serialization
                    try:
                        json.dumps(tool_result)
                    except (TypeError, ValueError) as e:
                        logging.error(f"Tool result serialization error: {str(e)}")
                        tool_result = {"type": "text", "text": str(converted_result)}
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

        print(f"\nTotal used: {self.total_tokens_used:,} / {Config.MAX_CONVERSATION_TOKENS:,}")

        bar_width = 40
        filled = int(used_percentage / 100 * bar_width)
        bar = "#" * filled + "-" * (bar_width - filled)

        print(f"[{bar}] {used_percentage:.1f}%")

        if remaining_tokens < 20000:
            print(f"Warning: Only {remaining_tokens:,} tokens remaining!")

        print("---")

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
                print("\nToken limit reached! Please reset the conversation.")
                return "Token limit reached! Please type 'reset' to start a new conversation."

            if response.stop_reason == "tool_use":
                print("\n  Handling Tool Use...\n")

                tool_results = []
                if getattr(response, 'content', None) and isinstance(response.content, list):
                    # Execute each tool in the response content
                    for content_block in response.content:
                        if content_block.type == "tool_use":
                            # Execute tool and get result (display is handled within _execute_tool)
                            result = await self._execute_tool(content_block)
                            
                            # Ensure result is properly serialized
                            def ensure_tool_serializable(obj):
                                """Ensure all objects are JSON serializable, with special handling for TextBlock and Rich objects."""
                                # Handle TextBlock objects (from prompt_toolkit)
                                if hasattr(obj, '__class__') and obj.__class__.__name__ == 'TextBlock':
                                    return str(obj.text) if hasattr(obj, 'text') else str(obj)
                                
                                # Handle Rich objects
                                if hasattr(obj, '__rich__'):
                                    from rich.console import Console
                                    console = Console(record=True, force_terminal=True)
                                    console.print(obj)
                                    return console.export_text(styles=True).strip()
                                
                                # Handle dictionaries recursively
                                if isinstance(obj, dict):
                                    return {k: ensure_tool_serializable(v) for k, v in obj.items()}
                                
                                # Handle lists and tuples recursively
                                if isinstance(obj, (list, tuple)):
                                    return [ensure_tool_serializable(item) for item in obj]
                                
                                # Handle objects with text attribute
                                if hasattr(obj, 'text'):
                                    return str(obj.text)
                                
                                # Handle objects with plain attribute
                                if hasattr(obj, 'plain'):
                                    return str(obj.plain)
                                
                                # Convert any other object to string
                                try:
                                    json.dumps(obj)  # Test if object is JSON serializable
                                    return obj
                                except (TypeError, ValueError):
                                    return str(obj)
                            
                            # Convert any TextBlock or Rich objects in the result
                            serialized_result = ensure_tool_serializable(result)

                            # Ensure the result is properly formatted as a text type
                            if isinstance(serialized_result, dict) and 'text' in serialized_result:
                                serialized_content = {
                                    "type": "text",
                                    "text": str(serialized_result['text'])
                                }
                            else:
                                serialized_content = {
                                    "type": "text",
                                    "text": str(serialized_result)
                                }

                            # Create the tool result with consistently formatted content
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
                        # Ensure all tool results are properly serialized
                        serialized_results = [ensure_tool_serializable(result) for result in tool_results]
                        # Ensure complete serialization of content array
                        serialized_content = []
                        for result in serialized_results:
                            if isinstance(result, dict) and 'content' in result:
                                # Handle nested content arrays
                                content_array = []
                                for content_item in result['content']:
                                    if isinstance(content_item, dict) and 'text' in content_item:
                                        content_array.append({
                                            'type': content_item.get('type', 'text'),
                                            'text': str(content_item['text'])
                                        })
                                result['content'] = content_array
                            serialized_content.append(result)
                        
                        self.conversation_history.append({
                            "role": "user",
                            "content": serialized_content
                        })
                    
                    # Properly await the recursive call
                    return await self._get_completion()

                else:
                    print("No tool content received despite 'tool_use' stop reason.")
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
                print("No content in final response.")
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
        Uses simple text-based spinner.
        """
        spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        i = 0
        try:
            while True:
                sys.stdout.write('\r\033[34mThinking... ' + spinner_chars[i] + '\033[0m')
                sys.stdout.flush()
                i = (i + 1) % len(spinner_chars)
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            sys.stdout.write('\r' + ' ' * 20 + '\r')  # Clear the spinner
            sys.stdout.flush()
            pass


    def _serialize_chat_content(self, content: Any) -> Dict[str, Any]:
        """
        Serialize content consistently, handling TextBlocks and other types.
        Always returns a Dict[str, Any] with 'type' and 'text' keys.
        """
        try:
            # Handle None or empty content
            if content is None:
                return {"type": "text", "text": ""}

            # Early handling of TextBlock and Rich objects
            if hasattr(content, '__class__'):
                # Handle TextBlock objects
                if content.__class__.__name__ == 'TextBlock':
                    return {"type": "text", "text": str(content.text) if hasattr(content, 'text') else str(content)}
                # Handle Rich objects
                if hasattr(content, '__rich__'):
                    from rich.console import Console
                    console = Console(record=True, force_terminal=True)
                    console.print(content)
                    return {"type": "text", "text": console.export_text(styles=True).strip()}

            # If already properly formatted, return as is
            if isinstance(content, dict):
                # Handle nested TextBlock or Rich objects in dict values
                if 'type' in content and 'text' in content:
                    if hasattr(content['text'], '__class__'):
                        if content['text'].__class__.__name__ == 'TextBlock':
                            content['text'] = str(content['text'].text) if hasattr(content['text'], 'text') else str(content['text'])
                        elif hasattr(content['text'], '__rich__'):
                            from rich.console import Console
                            console = Console(record=True, force_terminal=True)
                            console.print(content['text'])
                            content['text'] = console.export_text(styles=True).strip()
                    else:
                        content['text'] = str(content['text'])
                    return content

            # Handle lists by recursively serializing items first
            if isinstance(content, (list, tuple)):
                serialized_items = [self._serialize_chat_content(item) for item in content]
                # If all items are dicts with type/text, join their text values
                if all(isinstance(item, dict) and 'type' in item and 'text' in item for item in serialized_items):
                    return {"type": "text", "text": "\n".join(item['text'] for item in serialized_items)}
                # Otherwise return as JSON string
                return {"type": "text", "text": json.dumps([
                    item['text'] if isinstance(item, dict) and 'text' in item else str(item)
                    for item in serialized_items
                ], indent=2)}

            # Handle dictionaries
            if isinstance(content, dict):
                # Convert all values recursively
                converted_dict = {}
                for k, v in content.items():
                    if hasattr(v, '__class__'):
                        if v.__class__.__name__ == 'TextBlock':
                            converted_dict[k] = str(v.text) if hasattr(v, 'text') else str(v)
                        elif hasattr(v, '__rich__'):
                            from rich.console import Console
                            console = Console(record=True, force_terminal=True)
                            console.print(v)
                            converted_dict[k] = console.export_text(styles=True).strip()
                        else:
                            converted_dict[k] = self._serialize_chat_content(v)
                    else:
                        converted_dict[k] = v
                
                # If it's already a properly formatted content dict, return it
                if 'type' in converted_dict and 'text' in converted_dict:
                    converted_dict['text'] = str(converted_dict['text'])
                    return converted_dict
                
                # Otherwise, convert the whole dict to a string
                try:
                    return {"type": "text", "text": json.dumps(converted_dict, indent=2)}
                except:
                    return {"type": "text", "text": str(converted_dict)}

            # Handle objects with text or plain attributes
            if hasattr(content, 'plain'):
                return {"type": "text", "text": str(content.plain)}
            if hasattr(content, 'text'):
                return {"type": "text", "text": str(content.text)}

            # Final fallback: convert to string
            return {"type": "text", "text": str(content)}

        except Exception as e:
            logging.error(f"Error in _serialize_chat_content: {str(e)}")
            return {"type": "text", "text": f"Error serializing content: {str(e)}"}


    def _convert_textblock(self, obj: Any) -> Union[str, List[Any], Dict[str, Any]]:
        """Convert TextBlock objects to string, preserving other types including dictionaries."""
        if obj is None:
            return ""
        if isinstance(obj, (str, int, float, bool)):
            return str(obj)
        if isinstance(obj, (list, tuple)):
            return [self._convert_textblock(item) for item in obj]
        if isinstance(obj, dict):
            return {k: self._convert_textblock(v) for k, v in obj.items()}
        # Handle TextBlock objects
        if hasattr(obj, '__class__') and obj.__class__.__name__ == 'TextBlock':
            return str(obj.text) if hasattr(obj, 'text') else str(obj)
        # Handle Rich objects
        if hasattr(obj, '__rich__'):
            from rich.console import Console
            console = Console(record=True, force_terminal=True)
            console.print(obj)
            return console.export_text(styles=True).strip()
        return str(obj)

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
        # Input should already be converted from TextBlock in chat_loop()
        # Just ensure it's a string for processing
        if not isinstance(user_input, (str, list)):
            user_input = str(user_input)
            
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
            # Input is already converted in chat_loop(), just ensure it's a string
            def ensure_string(content):
                """Ensure content is a string."""
                if content is None:
                    return ""
                return str(content)

            # Convert and validate input
            if isinstance(user_input, str):
                # Already a string, just validate
                if not user_input.strip():
                    return "Message cannot be empty or contain only whitespace"
                serialized_input = [{"type": "text", "text": user_input}]
            elif isinstance(user_input, list):
                if not user_input:
                    return "Message list cannot be empty"
                
                serialized_input = []
                for item in user_input:
                    if isinstance(item, dict) and 'type' in item and 'text' in item:
                        # Convert the text value even if properly formatted
                        converted_text = ensure_string(item['text'])
                        if converted_text.strip():
                            serialized_input.append({"type": "text", "text": converted_text})
                    else:
                        # Convert other types
                        converted_text = ensure_string(item)
                        if converted_text.strip():
                            serialized_input.append({"type": "text", "text": converted_text})
                
                if not serialized_input:
                    return "Message cannot contain only empty or whitespace content"
            else:
                # Convert any other type
                converted_text = ensure_string(user_input)
                if converted_text.strip():
                    serialized_input = [{"type": "text", "text": converted_text}]
                else:
                    return "Message cannot be empty or contain only whitespace"

            # Debug: verify serialization
            try:
                json.dumps(serialized_input)
                logging.debug("Successfully serialized input: %s", json.dumps(serialized_input))
            except Exception as e:
                logging.error("Failed to serialize input: %s", str(e))

            # Input is already properly serialized, no need for additional conversion
            cleaned_input = serialized_input
            # Ensure conversation history is properly serialized
            try:
                # Convert any TextBlock objects in cleaned_input
                serialized_content = [self._serialize_chat_content(item) for item in cleaned_input]
                
                # Add serialized user message to conversation history
                history_entry = {
                    "role": "user",
                    "content": serialized_content
                }
                
                # Verify serialization before adding
                json.dumps(history_entry)
                self.conversation_history.append(history_entry)
                logging.debug("Successfully added user message to history")
            except Exception as e:
                logging.error(f"Failed to serialize conversation history: {str(e)}")
                # Fallback: add as plain text
                self.conversation_history.append({
                    "role": "user",
                    "content": [{"type": "text", "text": str(cleaned_input)}]
                })

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

            # Handle response serialization
            try:
                # Use _serialize_chat_content for consistent TextBlock handling
                serialized_response = self._serialize_chat_content(response)
                
                # Log assistant response
                self._log_message("assistant", serialized_response)

                # Use serialized response directly for conversation history
                history_content = [serialized_response]
            except Exception as e:
                logging.error(f"Error serializing response: {str(e)}")
                serialized_response = {"type": "text", "text": f"Error: {str(e)}"}
                history_content = [serialized_response]
            
            # Use _serialize_chat_content for consistent TextBlock handling
            # Ensure each history item is properly serialized
            cleaned_history = [self._serialize_chat_content(item) for item in history_content]
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": cleaned_history
            })

            # Capture context after successful response
            await self._capture_conversation_context()
            
            # Return serialized text, falling back to string representation if needed
            return str(serialized_response.get('text', str(response)))

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
            print("\n🔄 Assistant memory has been reset!")
        except Exception as e:
            error_msg = f"Critical error during reset operation: {str(e)}"
            logging.error(error_msg, exc_info=True)
            print(f"\nError: {error_msg}")
            raise  # Re-raise to ensure caller knows about the failure

        welcome_text = """
Claude Engineer v3. A self-improving assistant framework with tool creation

Type 'refresh' to reload available tools
Type 'reset' to clear conversation history
Type 'quit' to exit

Available tools:
"""
        print(welcome_text)
        self.display_available_tools()


async def main():
    """
    Entry point for the assistant CLI loop.
    Provides a prompt for user input and handles 'quit' and 'reset' commands.
    """
    session = PromptSession()

    try:
        assistant = Assistant()
    except ValueError as e:
        print(f"\nError: {str(e)}")
        print("Please ensure ANTHROPIC_API_KEY is set correctly.")
        return

    welcome_text = """
Claude Engineer v3. A self-improving assistant framework with tool creation

Type 'refresh' to reload available tools
Type 'reset' to clear conversation history
Type 'quit' to exit

Available tools:
"""
    print(welcome_text)
    assistant.display_available_tools()

    async def chat_loop():
        while True:
            try:
                # Use asyncio.shield to protect the prompt operation
                user_input = await asyncio.shield(session.prompt_async("You: "))
                
                # Handle TextBlock and Rich objects from prompt_toolkit immediately
                def convert_complex_objects(obj):
                    """Convert TextBlock and Rich objects to properly formatted strings."""
                    try:
                        # Handle None
                        if obj is None:
                            return ""
                            
                        # Handle TextBlock objects first and foremost
                        if hasattr(obj, '__class__') and obj.__class__.__name__ == 'TextBlock':
                            return str(obj.text) if hasattr(obj, 'text') else str(obj)
                            
                        # Handle Rich objects with proper color preservation
                        if hasattr(obj, '__rich__'):
                            from rich.console import Console
                            console = Console(record=True, force_terminal=True)
                            console.print(obj)
                            return console.export_text(styles=True).strip()
                            
                        # Handle dictionaries recursively
                        if isinstance(obj, dict):
                            return {k: convert_complex_objects(v) for k, v in obj.items()}
                            
                        # Handle lists and tuples recursively
                        if isinstance(obj, (list, tuple)):
                            return [convert_complex_objects(item) for item in obj]
                            
                        # Handle objects with text attribute
                        if hasattr(obj, 'text'):
                            return str(obj.text)
                            
                        # Handle objects with plain attribute
                        if hasattr(obj, 'plain'):
                            return str(obj.plain)
                            
                        # Test if object is JSON serializable
                        json.dumps(obj)
                        return obj
                    except (TypeError, ValueError):
                        return str(obj)
                    except Exception as e:
                        logging.error(f"Error in convert_complex_objects: {str(e)}")
                        return str(obj)

                # Convert any TextBlock or Rich objects in the input immediately
                user_input = convert_complex_objects(user_input)
                if not isinstance(user_input, str):
                    user_input = str(user_input)
                user_input = user_input.strip()
                
                # Verify the input is properly serializable
                try:
                    json.dumps({"text": user_input})
                except (TypeError, ValueError) as e:
                    logging.error(f"Input serialization error: {str(e)}")
                    user_input = str(user_input)

                if user_input.lower() == 'quit':
                    print("\n👋 Goodbye!")
                    break
                elif user_input.lower() == 'reset':
                    await asyncio.shield(assistant.reset())
                    continue

                try:
                    # Shield the chat operation to prevent cancellation during processing
                    response = await asyncio.shield(assistant.chat(user_input))
                except anthropic.APIConnectionError as conn_error:
                    print(f"\nConnection Error: {str(conn_error)}")
                    continue
                except anthropic.RateLimitError as rate_error:
                    print(f"\nRate Limit Error: {str(rate_error)}")
                    continue
                except anthropic.APIError as api_error:
                    print(f"\nAPI Error: {str(api_error)}")
                    continue
                except asyncio.TimeoutError:
                    print("\nRequest timed out")
                    continue
                except Exception as chat_error:
                    logging.error("Chat error:", exc_info=True)
                    print(f"\nUnexpected Error: {str(chat_error)}")
                    continue
                print("\nClaude Engineer:")
                print(response if isinstance(response, str) else str(response))

            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                logging.error("Fatal error in chat loop:", exc_info=True)
                print(f"\nFatal Error: {str(e)}")
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
