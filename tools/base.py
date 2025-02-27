from abc import ABC, abstractmethod
from typing import Dict

class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name that matches the regex ^[a-zA-Z0-9_-]{1,64}$"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Detailed description of what the tool does"""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict:
        """JSON Schema defining the expected parameters"""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool with given parameters"""
        pass

    def to_dict(self) -> Dict:
        """Convert tool properties to a dictionary format for Claude-3 API"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
