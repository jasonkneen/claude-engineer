from tools.agent_base import AgentBaseTool, AgentRole
from typing import Dict, Any, Optional, List
import json
import logging
from dataclasses import dataclass
import re
from concurrent.futures import ThreadPoolExecutor
import asyncio

@dataclass
class CompressionRule:
    pattern: str
    replacement: str
    priority: int = 0

class ContextManagerTool(AgentBaseTool):
    """Manages context compression and optimization.
    Handles context streams between agents while maintaining clarity.
    """

    description = """
    Manages context compression and optimization:
    - Compresses verbose contexts
    - Removes redundant information
    - Maintains context clarity
    - Prevents hallucinations
    - Optimizes token usage
    """
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["compress", "optimize", "clear", "get", "add_rule"],
                "description": "Action to perform"
            },
            "context_id": {
                "type": "string",
                "description": "Context identifier"
            },
            "context": {
                "type": "object",
                "description": "Context data to process"
            },
            "rule": {
                "type": "object",
                "description": "Compression rule to add"
            }
        },
        "required": ["action"]
    }

    def __init__(self, agent_id: str = "context_manager", role: AgentRole = AgentRole.CONTEXT, name: Optional[str] = None):
        """Initialize context manager with compression rules"""
        super().__init__(agent_id=agent_id, role=role, name=name)
        self.contexts: Dict[str, Dict[str, Any]] = {}
        self.compression_rules: List[CompressionRule] = [
            CompressionRule(
                pattern=r'\b(hello|hi)\b',
                replacement='greeting',
                priority=1
            ),
            CompressionRule(
                pattern=r'\b(this|that|the|a|an)\b\s+',
                replacement='',
                priority=2
            ),
            CompressionRule(
                pattern=r'\b(is|are|was|were)\b\s+',
                replacement='',
                priority=3
            ),
            CompressionRule(
                pattern=r'\s+',
                replacement=' ',
                priority=4
            ),
            CompressionRule(
                pattern=r'([.!?])\s+',
                replacement=r'\1',
                priority=5
            )
        ]
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.logger = logging.getLogger(__name__)

    def execute(self, **kwargs) -> str:
        """Execute context management operations.

        Args:
            action: Management action to perform
            context_id: Target context ID
            context: Context data to process
            rule: Compression rule to add

        Returns:
            Operation result as string
        """
        action = kwargs.get("action")
        context_id = kwargs.get("context_id", "default")

        try:
            if action == "compress":
                return self._compress_context(context_id, kwargs.get("context", {}))
            elif action == "optimize":
                return self._optimize_context(context_id)
            elif action == "clear":
                return self._clear_context(context_id)
            elif action == "get":
                return self._get_context(context_id)
            elif action == "add_rule":
                return self._add_compression_rule(kwargs.get("rule", {}))
            else:
                return f"Unknown action: {action}"

        except Exception as e:
            self.logger.error(f"Error in context manager: {str(e)}")
            return f"Error: {str(e)}"

    def _compress_context(self, context_id: str, context: Dict[str, Any]) -> str:
        """Compress context using defined rules"""
        if not context:
            return "No context provided"

        try:
            compressed = {}
            for key, value in context.items():
                if isinstance(value, str):
                    compressed_value = value
                    for rule in sorted(self.compression_rules, key=lambda x: x.priority):
                        pattern = rule.pattern if r'\b' in rule.pattern else fr'\b{rule.pattern}\b'
                        compressed_value = re.sub(
                            pattern,
                            rule.replacement,
                            compressed_value,
                            flags=re.IGNORECASE
                        )
                    compressed[key] = compressed_value.strip()
                else:
                    compressed[key] = value

            self.contexts[context_id] = compressed
            return f"Compressed context {context_id}"

        except Exception as e:
            return f"Compression error: {str(e)}"

    def _optimize_context(self, context_id: str) -> str:
        """Optimize context for token efficiency"""
        if context_id not in self.contexts:
            return f"Context {context_id} not found"

        try:
            context = self.contexts[context_id]
            optimized = {}

            # Remove redundant information
            seen_values = set()
            for key, value in context.items():
                if isinstance(value, str):
                    if value not in seen_values:
                        optimized[key] = value
                        seen_values.add(value)
                else:
                    optimized[key] = value

            self.contexts[context_id] = optimized
            return f"Optimized context {context_id}"

        except Exception as e:
            return f"Optimization error: {str(e)}"

    def _clear_context(self, context_id: str) -> str:
        """Clear specified context"""
        if context_id not in self.contexts:
            return f"Context {context_id} not found"

        del self.contexts[context_id]
        return f"Cleared context {context_id}"

    def _get_context(self, context_id: str) -> str:
        """Get specified context"""
        if context_id not in self.contexts:
            return f"Context {context_id} not found"

        return json.dumps(self.contexts[context_id], indent=2)

    def _add_compression_rule(self, rule: Dict[str, Any]) -> str:
        """Add new compression rule"""
        try:
            pattern = rule.get("pattern")
            replacement = rule.get("replacement")
            priority = rule.get("priority", 0)

            if not pattern or replacement is None:
                return "Invalid rule: missing pattern or replacement"

            # Validate regex pattern
            try:
                re.compile(pattern)
            except re.error:
                return f"Invalid regex pattern: {pattern}"

            new_rule = CompressionRule(
                pattern=pattern,
                replacement=replacement,
                priority=priority
            )
            self.compression_rules.append(new_rule)

            return f"Added compression rule: {pattern} -> {replacement}"

        except Exception as e:
            return f"Error adding rule: {str(e)}"

    async def close(self):
        """Clean up resources"""
        self._executor.shutdown(wait=True)
