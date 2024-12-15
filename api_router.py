import anthropic
import openai
from typing import Dict, Any, Optional
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
import os
from dataclasses import dataclass
from enum import Enum

class APIProvider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"

@dataclass
class APIConfig:
    model: str
    max_tokens: int
    temperature: float = 0.7
    stream: bool = False

class APIRouter:
    """Routes API requests to appropriate LLM providers.
    Handles both Anthropic and OpenAI endpoints with async support.
    """

    def __init__(self):
        """Initialize API clients and executor"""
        self.anthropic_client = anthropic.Anthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY')
        )
        self.openai_client = openai.Client(
            api_key=os.getenv('OPENAI_API_KEY')
        )
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.logger = logging.getLogger(__name__)

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

            if provider_enum == APIProvider.ANTHROPIC:
                return await self._anthropic_request(messages, config)
            elif provider_enum == APIProvider.OPENAI:
                return await self._openai_request(messages, config)

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
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                self._executor,
                lambda: self.anthropic_client.messages.create(
                    model=config.model,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    messages=messages
                )
            )
            return {
                "content": response.content,
                "usage": response.usage,
                "model": response.model,
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
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                self._executor,
                lambda: self.openai_client.chat.completions.create(
                    model=config.model,
                    messages=messages,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature
                )
            )
            return {
                "content": response.choices[0].message.content,
                "usage": response.usage,
                "model": response.model,
                "role": "assistant"
            }
        except Exception as e:
            self.logger.error(f"OpenAI API error: {str(e)}")
            raise

    async def close(self):
        """Clean up resources"""
        self._executor.shutdown(wait=True)
