import os
import json
import time
import tiktoken
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

class Memory:
    def __init__(self):
        # Configuration constants
        self.MAX_TOKEN_THRESHOLD = 3000  # Maximum tokens before compression
        self.MAX_MESSAGES = 50           # Maximum messages before compression
        self.TIME_THRESHOLD = 3600       # Time in seconds before compression
        self.PRESERVE_MESSAGES = 10      # Number of recent messages to preserve
        
        # Initialize memory state
        self.conversation_history = []
        self.important_decisions = []
        self.last_compression = time.time()
        self.encoder = tiktoken.get_encoding("cl100k_base")
        
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a new message to the conversation history."""
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "tokens": len(self.encoder.encode(content)),
            "metadata": metadata or {}
        }
        self.conversation_history.append(message)
        self._check_compression_triggers()
    
    def get_token_count(self) -> int:
        """Calculate total tokens in conversation history."""
        return sum(msg["tokens"] for msg in self.conversation_history)
    
    def _check_compression_triggers(self):
        """Check if any compression triggers are met."""
        current_time = time.time()
        total_tokens = self.get_token_count()
        
        should_compress = (
            total_tokens > self.MAX_TOKEN_THRESHOLD or
            len(self.conversation_history) > self.MAX_MESSAGES or
            (current_time - self.last_compression) > self.TIME_THRESHOLD
        )
        
        if should_compress:
            self._compress_context()
    
    def _score_message_importance(self, message: Dict[str, Any]) -> float:
        """Score message importance based on various factors."""
        score = 0.0
        content = message["content"].lower()
        
        # Score based on content indicators
        if "decision" in content or "conclusion" in content:
            score += 2.0
        if "important" in content or "key" in content:
            score += 1.5
        if "summary" in content or "result" in content:
            score += 1.0
            
        # Score based on metadata
        if message.get("metadata", {}).get("is_decision", False):
            score += 3.0
        if message.get("metadata", {}).get("is_summary", False):
            score += 2.0
            
        return score
    
    def _compress_context(self):
        """Compress conversation history while preserving important context."""
        if len(self.conversation_history) <= self.PRESERVE_MESSAGES:
            return
            
        # Preserve recent messages
        recent_messages = self.conversation_history[-self.PRESERVE_MESSAGES:]
        older_messages = self.conversation_history[:-self.PRESERVE_MESSAGES]
        
        # Score and sort older messages by importance
        scored_messages = [
            (msg, self._score_message_importance(msg))
            for msg in older_messages
        ]
        scored_messages.sort(key=lambda x: x[1], reverse=True)
        
        # Create summary of less important messages
        messages_to_summarize = [msg for msg, score in scored_messages[5:]]
        if messages_to_summarize:
            summary = self._generate_summary(messages_to_summarize)
            summary_message = {
                "role": "system",
                "content": summary,
                "timestamp": time.time(),
                "tokens": len(self.encoder.encode(summary)),
                "metadata": {"is_summary": True}
            }
            
            # Preserve important messages and add summary
            self.conversation_history = (
                [msg for msg, score in scored_messages[:5]] +
                [summary_message] +
                recent_messages
            )
        
        self.last_compression = time.time()
    
    def _generate_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Generate a concise summary of multiple messages."""
        # Group messages by role
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]
        
        summary_parts = [
            "Previous conversation summary:",
            f"- User made {len(user_messages)} requests, focusing on: " +
            self._extract_key_points(user_messages),
            f"- Assistant provided {len(assistant_messages)} responses, key points: " +
            self._extract_key_points(assistant_messages)
        ]
        
        return "\n".join(summary_parts)
    
    def _extract_key_points(self, messages: List[Dict[str, Any]]) -> str:
        """Extract key points from a list of messages."""
        # For now, return truncated content. In a real implementation,
        # you would want to use an LLM to generate better summaries
        key_points = []
        for msg in messages:
            content = msg["content"]
            if len(content) > 100:
                content = content[:97] + "..."
            key_points.append(content)
        return "; ".join(key_points)
    
    def get_context(self, max_tokens: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation context, optionally limited by token count."""
        if not max_tokens:
            return self.conversation_history
            
        result = []
        token_count = 0
        
        for message in reversed(self.conversation_history):
            msg_tokens = message["tokens"]
            if token_count + msg_tokens > max_tokens:
                break
            result.insert(0, message)
            token_count += msg_tokens
            
        return result
    
    def save_to_file(self, filename: str):
        """Save conversation history to a file."""
        with open(filename, 'w') as f:
            json.dump({
                'conversation_history': self.conversation_history,
                'important_decisions': self.important_decisions,
                'last_compression': self.last_compression
            }, f)
    
    def load_from_file(self, filename: str):
        """Load conversation history from a file."""
        with open(filename, 'r') as f:
            data = json.load(f)
            self.conversation_history = data['conversation_history']
            self.important_decisions = data['important_decisions']
            self.last_compression = data['last_compression']
            
class Assistant:
    def __init__(self):
        self.memory = Memory()
        
    # ... rest of the Assistant implementation remains the same ...

