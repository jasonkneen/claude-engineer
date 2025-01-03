from typing import Dict, Any, List, Optional, Callable
from enum import Enum
import asyncio
import logging
from dataclasses import dataclass

class ProtocolType(Enum):
    SSE = 'sse'
    HTTP = 'http'
    WEBSOCKET = 'websocket'

class ProtocolStatus(Enum):
    ACTIVE = 'active'
    FAILED = 'failed'
    FALLBACK = 'fallback'
    DISABLED = 'disabled'

@dataclass
class ProtocolConfig:
    type: ProtocolType
    priority: int
    enabled: bool = True
    max_failures: int = 3
    recovery_timeout: int = 30  # seconds
    health_check_interval: int = 10  # seconds

class ProtocolManager:
    def __init__(self):
        self._protocols: Dict[ProtocolType, ProtocolConfig] = {}
        self._status: Dict[ProtocolType, ProtocolStatus] = {}
        self._failure_counts: Dict[ProtocolType, int] = {}
        self._handlers: Dict[ProtocolType, Any] = {}
        self._fallback_chain: List[ProtocolType] = []
        self._logger = logging.getLogger(__name__)
        self._active_protocol: Optional[ProtocolType] = None

    def register_protocol(self, config: ProtocolConfig, handler: Any) -> None:
        """Register a protocol with its configuration and handler"""
        self._protocols[config.type] = config
        self._status[config.type] = ProtocolStatus.ACTIVE if config.enabled else ProtocolStatus.DISABLED
        self._failure_counts[config.type] = 0
        self._handlers[config.type] = handler
        self._update_fallback_chain()

    def _update_fallback_chain(self) -> None:
        """Update the fallback chain based on protocol priorities"""
        self._fallback_chain = sorted(
            [p_type for p_type, config in self._protocols.items() if config.enabled],
            key=lambda x: self._protocols[x].priority
        )

    async def get_active_handler(self) -> Optional[Any]:
        """Get the currently active protocol handler"""
        if not self._active_protocol:
            self._active_protocol = self._select_protocol()
        
        if self._active_protocol:
            return self._handlers[self._active_protocol]
        return None

    def _select_protocol(self) -> Optional[ProtocolType]:
        """Select the highest priority available protocol"""
        for protocol in self._fallback_chain:
            if self._status[protocol] in [ProtocolStatus.ACTIVE, ProtocolStatus.FALLBACK]:
                return protocol
        return None

    async def handle_protocol_failure(self, protocol_type: ProtocolType) -> None:
        """Handle protocol failure and trigger fallback if needed"""
        self._failure_counts[protocol_type] += 1
        self._logger.warning(f'Protocol {protocol_type.value} failure. Count: {self._failure_counts[protocol_type]}')

        if self._failure_counts[protocol_type] >= self._protocols[protocol_type].max_failures:
            await self._trigger_fallback(protocol_type)

    async def _trigger_fallback(self, failed_protocol: ProtocolType) -> None:
        """Trigger fallback to next available protocol"""
        self._status[failed_protocol] = ProtocolStatus.FAILED
        self._logger.info(f'Protocol {failed_protocol.value} marked as failed, triggering fallback')

        # Find next available protocol
        current_index = self._fallback_chain.index(failed_protocol)
        for protocol in self._fallback_chain[current_index + 1:]:
            if self._status[protocol] != ProtocolStatus.FAILED:
                self._active_protocol = protocol
                self._status[protocol] = ProtocolStatus.FALLBACK
                self._logger.info(f'Falling back to protocol: {protocol.value}')
                return

        self._logger.error('No available fallback protocols')

    async def start_recovery_monitoring(self) -> None:
        """Start monitoring failed protocols for recovery"""
        while True:
            for protocol in self._protocols:
                if self._status[protocol] == ProtocolStatus.FAILED:
                    await self._check_protocol_recovery(protocol)
            await asyncio.sleep(min(p.recovery_timeout for p in self._protocols.values()))

    async def _check_protocol_recovery(self, protocol: ProtocolType) -> None:
        """Check if a failed protocol has recovered"""
        try:
            # Implement protocol-specific health check here
            config = self._protocols[protocol]
            handler = self._handlers[protocol]
            
            # Example health check (should be implemented per protocol)
            if await self._health_check(protocol, handler):
                self._status[protocol] = ProtocolStatus.ACTIVE
                self._failure_counts[protocol] = 0
                self._logger.info(f'Protocol {protocol.value} has recovered')
                self._update_fallback_chain()

        except Exception as e:
            self._logger.error(f'Recovery check failed for {protocol.value}: {str(e)}')

    async def _health_check(self, protocol: ProtocolType, handler: Any) -> bool:
        """Perform protocol-specific health check"""
        try:
            if protocol == ProtocolType.SSE:
                # Implement SSE-specific health check
                return await handler.check_connection()
            elif protocol == ProtocolType.HTTP:
                # Implement HTTP-specific health check
                return await handler.ping()
            return False
        except Exception:
            return False

    def get_protocol_status(self, protocol: ProtocolType) -> ProtocolStatus:
        """Get current status of a protocol"""
        return self._status.get(protocol, ProtocolStatus.DISABLED)

    def get_active_protocol(self) -> Optional[ProtocolType]:
        """Get currently active protocol type"""
        return self._active_protocol