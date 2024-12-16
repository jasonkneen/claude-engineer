from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import asyncio

class BaseTool(ABC):
    """Base class for all tools."""

    def __init__(self, name: Optional[str] = None):
        self._name = name or self.__class__.__name__.lower()
        self._initialized = False

    async def initialize(self):
        """Optional async initialization hook."""
        if not self._initialized:
            await self._initialize()
            self._initialized = True

    async def _initialize(self):
        """Internal async initialization hook for subclasses to override."""
        pass

    @property
    def name(self) -> str:
        """Get the tool name."""
        return self._name

    @property
    @abstractmethod
    def description(self) -> str:
        """Get the tool description."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """Get the input schema for the tool."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool's main functionality."""
        pass
