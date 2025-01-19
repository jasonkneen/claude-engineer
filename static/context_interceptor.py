from enum import Enum
from typing import Dict, Any, Callable, List, Optional
from tools.base import BaseTool

class InterceptionPoint(Enum):
    PRE_COMPLETION = "pre_completion"
    POST_COMPLETION = "post_completion"

class ContextInterceptor(BaseTool):
    """Base class for context interception tools
    
    Provides a standard interface for tools that need to intercept and modify
    context before or after completions are generated.
    """

    @property
    def name(self) -> str:
        return "base_context_interceptor"

    @property
    def description(self) -> str:
        return "Base interceptor for modifying context before and after completions"

    @property
    def input_schema(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "context": {
                    "type": "object",
                    "description": "The context to intercept and modify"
                },
                "point": {
                    "type": "string",
                    "enum": ["pre_completion", "post_completion"],
                    "description": "The interception point"
                }
            },
            "required": ["context", "point"]
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the interceptor"""
        context = kwargs.get("context", {})
        point = InterceptionPoint(kwargs.get("point"))
        return self.intercept(context, point)

    def __init__(self):
        super().__init__()
        self.hooks = {
            InterceptionPoint.PRE_COMPLETION: [],
            InterceptionPoint.POST_COMPLETION: [] 
        }
        
    def register_hook(self, point: InterceptionPoint, 
                    callback: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        """Register a callback function to be called at a specific interception point
        
        Args:
            point: When the callback should be executed (pre/post completion)
            callback: Function that takes and returns a context dict
        """
        self.hooks[point].append(callback)
        
    def intercept(self, context: Dict[str, Any], 
                point: InterceptionPoint) -> Dict[str, Any]:
        """Execute all registered hooks for a given interception point
        
        Args:
            context: The current context dictionary
            point: The interception point being executed
            
        Returns:
            Modified context dictionary after all hooks are executed
        """
        modified_context = context.copy()
        for hook in self.hooks[point]:
            modified_context = hook(modified_context)
        return modified_context
        
    def modify_conversation_history(self, context: Dict[str, Any],
                                modifier: Callable[[List], List]) -> Dict[str, Any]:
        """Helper to modify the conversation history
        
        Args:
            context: The context dictionary
            modifier: Function that takes and returns a conversation history list
            
        Returns:
            Context with modified conversation history
        """
        if "conversation_history" in context:
            modified = context.copy()
            modified["conversation_history"] = modifier(context["conversation_history"])
            return modified
        return context
        
    def get_last_message(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Helper to get the last message in conversation history
        
        Args:
            context: The context dictionary
            
        Returns:
            The last message or None if history is empty
        """
        if "conversation_history" in context and context["conversation_history"]:
            return context["conversation_history"][-1]
        return None
        
    def update_metadata(self, context: Dict[str, Any], 
                    updates: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to update context metadata
        
        Args:
            context: The context dictionary 
            updates: Dictionary of metadata updates to apply
            
        Returns:
            Context with updated metadata
        """
        modified = context.copy()
        modified.update(updates)
        return modified

