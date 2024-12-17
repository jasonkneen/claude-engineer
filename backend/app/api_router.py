import anthropic
import openai
from typing import Dict, Any, Optional, List
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
import os
from dataclasses import dataclass
from enum import Enum
from contextlib import AbstractContextManager

class APIProvider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"

@dataclass
class APIConfig:
    model: str
    max_tokens: int
    temperature: float = 0.7
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    system: Optional[str] = None

class APIRouter(AbstractContextManager):
    """Routes API requests to appropriate LLM providers.
    Handles both Anthropic and OpenAI endpoints with async support.
    """

    def __init__(self) -> None:
        """Initialize API clients and executor"""
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.anthropic_client = None
        self.openai_client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup resources
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Implement standard context manager exit."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=True)

    async def setup(self) -> None:
        """Async setup of API clients"""
        await self._setup_clients()

    async def _setup_clients(self) -> None:
        """Set up API clients with proper error handling"""
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')

        if not anthropic_key:
            logger.error("Missing ANTHROPIC_API_KEY environment variable")
            raise APIProviderError("Anthropic API key not found")

        if not openai_key:
            logger.error("Missing OPENAI_API_KEY environment variable")
            raise APIProviderError("OpenAI API key not found")

        try:
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
            self.openai_client = openai.Client(api_key=openai_key)
        except Exception as e:
            logger.error(f"Failed to initialize API clients: {str(e)}")
            self._executor.shutdown(wait=False)
            raise APIProviderError(f"Failed to initialize API clients: {str(e)}")

    async def route_request(
        self,
        provider: str,
        messages: list,
        config: Optional[APIConfig] = None
    ) -> Dict[str, Any]:
        """Route request to specified provider.

        Args:
            provider: Provider name ('anthropic' or 'openai')
            messages: List of conversation messages
            config: Optional API configuration

        Returns:
            API response as dict
        """
        try:
            provider_enum = APIProvider(provider.lower())
            if config is None:
                config = self._get_default_config(provider_enum)

            # Format messages for API request
            formatted_messages = []
            for msg in messages:
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    formatted_messages.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })

            # Get response from appropriate provider
            if provider_enum == APIProvider.ANTHROPIC:
                response = await self._anthropic_request(formatted_messages, config)
            elif provider_enum == APIProvider.OPENAI:
                response = await self._openai_request(formatted_messages, config)
            else:
                raise ValueError(f"Unsupported provider: {provider}")

            # Ensure response is properly formatted
            if isinstance(response, dict):
                return {
                    "content": str(response.get("content", "")),
                    "role": "assistant",
                    "usage": {
                        "input_tokens": int(response.get("usage", {}).get("input_tokens", 0)),
                        "output_tokens": int(response.get("usage", {}).get("output_tokens", 0))
                    },
                    "model": str(response.get("model", "unknown"))
                }
            else:
                return {
                    "content": str(response),
                    "role": "assistant",
                    "usage": {"input_tokens": 0, "output_tokens": 0},
                    "model": "unknown"
                }

        except Exception as e:
            self.logger.error(f"Error routing request: {str(e)}")
            raise

    def _get_default_config(self, provider: APIProvider) -> APIConfig:
        """Get default configuration for provider"""
        if provider == APIProvider.ANTHROPIC:
            return APIConfig(
                model="claude-3-sonnet-20240229",
                max_tokens=4096,
                temperature=0.7
            )
        else:
            return APIConfig(
                model="gpt-4-turbo-preview",
                max_tokens=4096,
                temperature=0.7
            )

    async def _anthropic_request(
        self,
        messages: list,
        config: APIConfig
    ) -> Dict[str, Any]:
        """Handle Anthropic API request"""
        try:
            # Format messages for Anthropic API
            formatted_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    formatted_messages.append({
                        "role": msg.get("role", "user"),
                        "content": str(msg.get("content", ""))
                    })

            # Make API request
            response = await self.anthropic_client.messages.create(
                model=config.model,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                messages=formatted_messages
            )

            # Extract content from response
            content = response.content[0].text if isinstance(response.content, list) else response.content

            return {
                "content": str(content),
                "usage": {
                    "input_tokens": getattr(response.usage, "input_tokens", 0),
                    "output_tokens": getattr(response.usage, "output_tokens", 0)
                },
                "model": str(response.model),
                "role": "assistant"
            }
        except Exception as e:
            self.logger.error(f"Anthropic API error: {str(e)}")
            raise

    async def _openai_request(
        self,
        messages: list,
        config: APIConfig
    ) -> Dict[str, Any]:
        """Handle OpenAI API request"""
        try:
            # Format messages for OpenAI API
            formatted_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    formatted_messages.append({
                        "role": msg.get("role", "user"),
                        "content": str(msg.get("content", ""))
                    })

            # Make API request
            response = await self.openai_client.chat.completions.create(
                model=config.model,
                messages=formatted_messages,
                max_tokens=config.max_tokens,
                temperature=config.temperature
            )

            # Extract content and format response
            content = response.choices[0].message.content if response.choices else ""

            return {
                "content": str(content),
                "usage": {
                    "input_tokens": int(getattr(response.usage, "prompt_tokens", 0)),
                    "output_tokens": int(getattr(response.usage, "completion_tokens", 0))
                },
                "model": str(response.model),
                "role": "assistant"
            }
        except Exception as e:
            self.logger.error(f"OpenAI API error: {str(e)}")
            raise

    async def close(self):
        """Clean up resources"""
        self._executor.shutdown(wait=True)
