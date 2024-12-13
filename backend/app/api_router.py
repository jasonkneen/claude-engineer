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
        self.logger = logging.getLogger(__name__)

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
            # Validate and prepare provider
            provider_enum = APIProvider(provider.lower())
            if config is None:
                config = self._get_default_config(provider_enum)

            # Format messages for API request
            formatted_messages = []
            for msg in messages:
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    formatted_messages.append({
                        'role': str(msg['role']),
                        'content': str(msg['content'])
                    })

            # Get response from appropriate provider
            try:
                # Make API request
                if provider_enum == APIProvider.ANTHROPIC:
                    api_response = await self._anthropic_request(formatted_messages, config)
                elif provider_enum == APIProvider.OPENAI:
                    api_response = await self._openai_request(formatted_messages, config)
                else:
                    raise ValueError(f"Unsupported provider: {provider}")

                # Format response
                if isinstance(api_response, dict):
                    content = str(api_response.get("content", ""))
                    usage = api_response.get("usage", {})
                    model = str(api_response.get("model", "unknown"))
                else:
                    content = str(api_response)
                    usage = {"input_tokens": 0, "output_tokens": 0}
                    model = "unknown"

                # Return formatted response
                return {
                    "content": content,
                    "role": "assistant",
                    "usage": {
                        "input_tokens": int(usage.get("input_tokens", 0)),
                        "output_tokens": int(usage.get("output_tokens", 0))
                    },
                    "model": model
                }

            except Exception as provider_error:
                self.logger.error(f"Provider error: {str(provider_error)}")
                return {
                    "content": f"Error: {str(provider_error)}",
                    "role": "assistant",
                    "usage": {"input_tokens": 0, "output_tokens": 0},
                    "model": "unknown"
                }

        except Exception as e:
            self.logger.error(f"Error routing request: {str(e)}")
            return {
                "content": f"Error: {str(e)}",
                "role": "assistant",
                "usage": {"input_tokens": 0, "output_tokens": 0},
                "model": "unknown"
            }

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
                        "role": str(msg.get("role", "user")),
                        "content": str(msg.get("content", ""))
                    })

            # Create API request parameters
            request_params = {
                "model": config.model,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
                "messages": formatted_messages
            }

            # Make API request
            response = await self.anthropic_client.messages.create(**request_params)

            # Extract content from response
            content = ""
            if response and hasattr(response, 'content'):
                if isinstance(response.content, list) and response.content:
                    content = response.content[0].text
                else:
                    content = response.content

            # Get usage information
            usage = {
                "input_tokens": 0,
                "output_tokens": 0
            }
            if hasattr(response, 'usage'):
                usage = {
                    "input_tokens": int(getattr(response.usage, "input_tokens", 0)),
                    "output_tokens": int(getattr(response.usage, "output_tokens", 0))
                }

            # Return formatted response
            return {
                "content": str(content),
                "usage": usage,
                "model": str(getattr(response, "model", config.model)),
                "role": "assistant"
            }

        except Exception as e:
            self.logger.error(f"Anthropic API error: {str(e)}")
            return {
                "content": f"Error: {str(e)}",
                "usage": {"input_tokens": 0, "output_tokens": 0},
                "model": config.model,
                "role": "assistant"
            }

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
                        "role": str(msg.get("role", "user")),
                        "content": str(msg.get("content", ""))
                    })

            # Create API request parameters
            request_params = {
                "model": config.model,
                "messages": formatted_messages,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature
            }

            try:
                # Make API request
                response = await self.openai_client.chat.completions.create(**request_params)

                # Extract content from response
                content = ""
                if response and hasattr(response, 'choices') and response.choices:
                    content = response.choices[0].message.content

                # Get usage information
                usage = {
                    "input_tokens": 0,
                    "output_tokens": 0
                }
                if hasattr(response, 'usage'):
                    usage = {
                        "input_tokens": int(getattr(response.usage, "prompt_tokens", 0)),
                        "output_tokens": int(getattr(response.usage, "completion_tokens", 0))
                    }

                # Format response
                return {
                    "content": str(content),
                    "usage": usage,
                    "model": str(getattr(response, "model", config.model)),
                    "role": "assistant"
                }

            except Exception as api_error:
                self.logger.error(f"OpenAI API request error: {str(api_error)}")
                return {
                    "content": f"API Error: {str(api_error)}",
                    "usage": {"input_tokens": 0, "output_tokens": 0},
                    "model": config.model,
                    "role": "assistant"
                }

        except Exception as e:
            self.logger.error(f"OpenAI message formatting error: {str(e)}")
            return {
                "content": f"Error: {str(e)}",
                "usage": {"input_tokens": 0, "output_tokens": 0},
                "model": config.model,
                "role": "assistant"
            }

    async def close(self):
        """Clean up resources"""
        self._executor.shutdown(wait=True)
