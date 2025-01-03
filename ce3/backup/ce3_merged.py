import os
import json
import re
import tiktoken
from datetime import datetime
from typing import List, Dict, Any, Optional
from tools.base import BaseTool
from tools.filediffmergetool import FileDiffMergeTool
from tools.contextmanagertool import ContextManagerTool
from tools.memorypersistencetool import MemoryPersistenceTool
from tools.messagehistorycompressiontool import MessageHistoryCompressionTool

class Memory:
    def __init__(self):
        self.conversation_history: List[Dict] = []
        self.summary: str = ""
        self.encoder = tiktoken.encoding_for_model("gpt-4")
        self.max_tokens = 8000  # Buffer for model's context window
        self.token_count = 0
        self.compression_threshold = 6000  # When to trigger compression
        self.min_messages_before_compression = 10
        self.keep_recent_messages = 5  # Number of recent messages to keep in full

    def add_message(self, role: str, content: str) -> None:
        tokens = len(self.encoder.encode(content))
        message = {"role": role, "content": content, "tokens": tokens, "timestamp": datetime.now().isoformat()}
        self.conversation_history.append(message)
        self.token_count += tokens
        
        if self._should_compress():
            self._compress_context()

    def get_context(self) -> List[Dict]:
        if self.summary:
            summary_message = {"role": "system", "content": f"Previous conversation summary: {self.summary}"}
            return [summary_message] + self.conversation_history[-self.keep_recent_messages:]
        return self.conversation_history

    def _should_compress(self) -> bool:
        return (
            len(self.conversation_history) > self.min_messages_before_compression
            and self.token_count > self.compression_threshold
        )

    def _compress_context(self) -> None:
        if len(self.conversation_history) <= self.keep_recent_messages:
            return

        # Keep recent messages
        recent_messages = self.conversation_history[-self.keep_recent_messages:]
        to_compress = self.conversation_history[:-self.keep_recent_messages]

        # Create summary of older messages
        messages_to_summarize = [f"{m['role']}: {m['content']}" for m in to_compress]
        summary_text = "\n".join(messages_to_summarize)
        
        # Use compression tool for summarization
        compression_tool = MessageHistoryCompressionTool()
        self.summary = compression_tool.execute(text=summary_text, operation="summarize")

        # Update conversation history and token count
        self.conversation_history = recent_messages
        self.token_count = sum(msg["tokens"] for msg in recent_messages)
        self.token_count += len(self.encoder.encode(self.summary))

    def persist(self) -> None:
        persistence_tool = MemoryPersistenceTool()
        data = {
            "conversation_history": self.conversation_history,
            "summary": self.summary,
            "token_count": self.token_count
        }
        persistence_tool.execute(data=data, operation="save")

    def load(self) -> None:
        persistence_tool = MemoryPersistenceTool()
        data = persistence_tool.execute(operation="load")
        if data:
            self.conversation_history = data.get("conversation_history", [])
            self.summary = data.get("summary", "")
            self.token_count = data.get("token_count", 0)

class Assistant:
    def __init__(self, model="gpt-4"):
        self.model = model
        self.memory = Memory()
        self._load_tools()
        self.context_manager = ContextManagerTool()
        
    def _load_tools(self):
        self.tools = []
        tools_dir = "tools"
        for file in os.listdir(tools_dir):
            if file.endswith('.py') and not file.startswith('__'):
                module_name = file[:-3]
                try:
                    module = __import__(f"tools.{module_name}", fromlist=['*'])
                    for item in dir(module):
                        obj = getattr(module, item)
                        if isinstance(obj, type) and issubclass(obj, BaseTool) and obj != BaseTool:
                            tool = obj()
                            self.tools.append(tool)
                except Exception as e:
                    print(f"Error loading tool {module_name}: {e}")

    def chat(self, message: str) -> str:
        self.memory.add_message("user", message)
        
        # Extract potential tool calls from message
        tool_matches = []
        for tool in self.tools:
            if tool.should_handle(message):
                tool_matches.append(tool)

        response = ""
        if tool_matches:
            # Handle tool execution
            for tool in tool_matches:
                try:
                    result = tool.execute(message=message)
                    response += f"{result}\n"
                except Exception as e:
                    response += f"Error executing {tool.__class__.__name__}: {str(e)}\n"
        else:
            # Regular chat response
            context = self.memory.get_context()
            response = self.context_manager.execute(
                context=context,
                message=message,
                model=self.model
            )

        self.memory.add_message("assistant", response)
        self.memory.persist()
        return response

    def reset(self):
        """Reset the conversation history"""
        self.memory = Memory()

if __name__ == "__main__":
    assistant = Assistant()
    print("Assistant initialized. Type 'quit' to exit.")
    
    while True:
        user_input = input("> ")
        if user_input.lower() in ['quit', 'exit']:
            break
        
        response = assistant.chat(user_input)
        print(response)

