from typing import Dict, Any, Optional, Callable
from enum import Enum
import asyncio
import logging
from dataclasses import dataclass
from protocol_manager import ProtocolType, ProtocolStatus, ProtocolManager

class FallbackStrategy(Enum):
    SEQUENTIAL = 'sequential'
    PRIORITY_BASED = 'priority_based'
    ROUND_ROBIN = 'round_robin'

@dataclass
class FallbackConfig:
    strategy: FallbackStrategy
    retry_interval: int = 5  # seconds
    max_retries: int = 3
    timeout: int = 10  # seconds

class FallbackHandler:
    def __init__(self, protocol_manager: ProtocolManager, config: FallbackConfig):
        self._protocol_manager = protocol_manager
        self._config = config
        self._logger = logging.getLogger(__name__)
        self._retry_counts: Dict[ProtocolType, int] = {}
        self._fallback_in_progress = False

    async def handle_request(self, request_func: Callable, *args, **kwargs) -> Optional[Any]:
        """Handle request with automatic fallback on failure"""
        try:
            handler = await self._protocol_manager.get_active_handler()
            if not handler:
                raise Exception('No active protocol handler available')

            return await self._execute_with_fallback(handler, request_func, *args, **kwargs)

        except Exception as e:
            self._logger.error(f'Request failed: {str(e)}')
            return None

    async def _execute_with_fallback(self, handler: Any, request_func: Callable, *args, **kwargs) -> Optional[Any]:
        """Execute request with fallback handling"""
        active_protocol = self._protocol_manager.get_active_protocol()
        if not active_protocol:
            return None

        try:
            return await asyncio.wait_for(
                request_func(handler, *args, **kwargs),
                timeout=self._config.timeout
            )

        except Exception as e:
            self._logger.warning(f'Request failed on {active_protocol.value}: {str(e)}')
            if not self._fallback_in_progress:
                return await self._trigger_fallback(active_protocol, request_func, *args, **kwargs)
            return None

    async def _trigger_fallback(self, failed_protocol: ProtocolType, request_func: Callable, *args, **kwargs) -> Optional[Any]:
        """Trigger fallback process"""
        self._fallback_in_progress = True
        try:
            await self._protocol_manager.handle_protocol_failure(failed_protocol)
            
            retry_count = self._retry_counts.get(failed_protocol, 0)
            if retry_count < self._config.max_retries:
                self._retry_counts[failed_protocol] = retry_count + 1
                await asyncio.sleep(self._config.retry_interval)
                
                new_handler = await self._protocol_manager.get_active_handler()
                if new_handler:
                    self._logger.info(f'Attempting request with fallback protocol')
                    return await self._execute_with_fallback(new_handler, request_func, *args, **kwargs)

        except Exception as e:
            self._logger.error(f'Fallback failed: {str(e)}')
        finally:
            self._fallback_in_progress = False
        return None

    async def monitor_protocol_health(self) -> None:
        """Monitor protocol health and manage recovery"""
        while True:
            try:
                active_protocol = self._protocol_manager.get_active_protocol()
                if active_protocol:
                    handler = await self._protocol_manager.get_active_handler()
                    if handler:
                        # Perform health check
                        is_healthy = await self._check_protocol_health(active_protocol, handler)
                        if not is_healthy:
                            await self._protocol_manager.handle_protocol_failure(active_protocol)

                await asyncio.sleep(self._config.retry_interval)

            except Exception as e:
                self._logger.error(f'Health monitoring error: {str(e)}')
                await asyncio.sleep(self._config.retry_interval)

    async def _check_protocol_health(self, protocol: ProtocolType, handler: Any) -> bool:
        """Check health of a specific protocol"""
        try:
            if protocol == ProtocolType.SSE:
                return await handler.get_connection_state() == 'connected'
            elif protocol == ProtocolType.HTTP:
                return await handler.check_health()
            return False
        except Exception:
            return False