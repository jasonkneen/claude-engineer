#!/usr/bin/env python3
from typing import Dict, Any, Optional


class CE3EventHandler:
    """Handles context events and modifications in CE3"""

    def __init__(self):
        self.context_stats = {"total_tokens": 0, "conversation_turns": 0}

    def process_context(self, context: Dict) -> Dict:
        """Main entry point for context processing

        Args:
            context: The full context dictionary containing conversation history and metadata

        Returns:
            Modified context dictionary
        """
        # Clean error messages
        context = self._clean_error_messages(context)

        # Update stats
        self._update_context_stats(context)

        return context

    def _clean_error_messages(self, context: Dict) -> Dict:
        """Remove duplicate error messages and clean up formatting"""
        if "conversation_history" not in context:
            return context

        seen_errors = set()
        cleaned_history = []

        for message in context["conversation_history"]:
            if "content" in message:
                content = message["content"]
                if isinstance(content, list):
                    # Handle list of content blocks
                    has_error = False
                    for block in content:
                        # Handle both dict and object content blocks
                        block_type = (
                            getattr(block, "type", None)
                            if hasattr(block, "type")
                            else block.get("type")
                        )
                        block_text = (
                            getattr(block, "text", None)
                            if hasattr(block, "text")
                            else block.get("text", "")
                        )

                        if (
                            block_type == "text"
                            and isinstance(block_text, str)
                            and "error" in block_text.lower()
                        ):
                            error_msg = self._extract_error_message(block_text)
                            if error_msg not in seen_errors:
                                seen_errors.add(error_msg)
                                has_error = True
                                break
                    cleaned_history.append(message)
                elif isinstance(content, str) and "error" in content.lower():
                    # Legacy string content handling
                    error_msg = self._extract_error_message(content)
                    if error_msg not in seen_errors:
                        seen_errors.add(error_msg)
                        cleaned_history.append(message)
                    else:
                        cleaned_history.append(message)
                else:
                    # Non-error content, preserve as is
                    cleaned_history.append(message)
            else:
                cleaned_history.append(message)

        context["conversation_history"] = cleaned_history
        return context

    def _extract_error_message(self, error_text: str) -> str:
        """Extract the core error message without stack traces"""
        # Split on common error delimiters
        lines = error_text.split("\n")
        for line in lines:
            if "error" in line.lower():
                return line.strip()
        return error_text.split("\n")[0].strip()

    def _update_context_stats(self, context: Dict) -> None:
        """Update context statistics"""
        if "conversation_history" in context:
            self.context_stats["conversation_turns"] = (
                len(context["conversation_history"]) // 2
            )

        if "total_tokens_used" in context:
            self.context_stats["total_tokens"] = context["total_tokens_used"]

    def get_stats(self) -> Dict:
        """Get current context statistics"""
        return self.context_stats.copy()
