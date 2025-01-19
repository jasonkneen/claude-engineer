#!/usr/bin/env python3
# ce3.py
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
from prompt_toolkit import prompt
from prompt_toolkit.styles import Style
from prompts.system_prompts import SystemPrompts
from infinite_context import InfiniteContext

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
    - Infinite context management with compression and indexing.
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

        self.tools = self._load_tools()
        
        # Initialize InfiniteContext
        self.context_manager = InfiniteContext()

    # ... [previous methods remain unchanged until chat] ...

    def _get_completion(self):
        """
        Get a completion from the Anthropic API.
        Handles both text-only and multimodal messages.
        """
        try:
            # Get relevant context based on the last user message
            last_user_message = next((msg for msg in reversed(self.conversation_history) 
                                    if msg["role"] == "user"), None)
            
            if last_user_message:
                if isinstance(last_user_message["content"], str):
                    query = last_user_message["content"]
                else:
                    # Handle multimodal content by extracting text
                    query = " ".join(str(item) for item in last_user_message["content"])
                    
                relevant_context = self.context_manager.get_relevant_context(query)
                
                # Create temporary conversation history with relevant context
                temp_history = relevant_context + self.conversation_history[-2:] if len(self.conversation_history) > 1 else []
            else:
                temp_history = self.conversation_history

            response = self.client.messages.create(
                model=Config.MODEL,
                max_tokens=min(
                    Config.MAX_TOKENS,
                    Config.MAX_CONVERSATION_TOKENS - self.total_tokens_used
                ),
                temperature=self.temperature,
                tools=self.tools,
                messages=temp_history,
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

                    # Add tool usage to context manager and continue
                    self.context_manager.add_context({
                        "role": "assistant",
                        "content": response.content
                    })
                    self.context_manager.add_context({
                        "role": "user",
                        "content": tool_results
                    })
                    return self._get_completion()  # Recursive call to continue the conversation

                else:
                    self.console.print("[red]No tool content received despite 'tool_use' stop reason.[/red]")
                    return "Error: No tool content received"

            # Final assistant response
            if (getattr(response, 'content', None) and 
                isinstance(response.content, list) and 
                response.content):
                final_content = response.content[0].text
                
                # Add final response to context manager
                self.context_manager.add_context({
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

    def chat(self, user_input):
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
                self.reset()
                return "Conversation reset!"
            elif user_input.lower() == 'quit':
                return "Goodbye!"

        try:
            # Add user message to context manager
            message = {
                "role": "user",
                "content": user_input  # This can be either string or list
            }
            self.context_manager.add_context(message)
            
            # Keep last message in conversation history for immediate context
            self.conversation_history = [message]

            # Show thinking indicator if enabled
            if self.thinking_enabled:
                with Live(Spinner('dots', text='Thinking...', style="cyan"), 
                         refresh_per_second=10, transient=True):
                    response = self._get_completion()
            else:
                response = self._get_completion()

            return response

        except Exception as e:
            logging.error(f"Error in chat: {str(e)}")
            return f"Error: {str(e)}"

    def reset(self):
        """
        Reset the assistant's memory, token usage, and context.
        """
        self.conversation_history = []
        self.total_tokens_used = 0
        self.context_manager.clear()
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


# ... [rest of the file remains unchanged] ...