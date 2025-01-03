from typing import Dict, Any, Optional, List
from protocol_manager import ProtocolManager, ProtocolType, ProtocolConfig, ProtocolStatus
from fallback_handler import FallbackHandler, FallbackConfig, FallbackStrategy
from enhanced_sse import EnhancedSSETransport, ConnectionConfig
from monitoring import MonitoringSystem, MetricType
import asyncio
import logging
from dataclasses import dataclass

@dataclass
class TransportConfig:
    sse_config: ConnectionConfig
    fallback_config: FallbackConfig
    monitoring_enabled: bool = True
    health_check_interval: int = 30

class MCPTransportSystem:
    def __init__(self, config: TransportConfig):
        self._config = config
        self._logger = logging.getLogger(__name__)
        
        # Initialize components
        self._protocol_manager = ProtocolManager()
        self._fallback_handler = FallbackHandler(
            protocol_manager=self._protocol_manager,
            config=config.fallback_config
        )
        
        if config.monitoring_enabled:
            self._monitoring = MonitoringSystem(health_check_interval=config.health_check_interval)
        
        # Initialize protocols
        self._init_protocols()
        
        # Background tasks
        self._tasks: List[asyncio.Task] = []

    def _init_protocols(self) -> None:
        # Initialize SSE Transport
        sse_handler = EnhancedSSETransport(config=self._config.sse_config)
        self._protocol_manager.register_protocol(
            config=ProtocolConfig(
                type=ProtocolType.SSE,
                priority=1,
                enabled=True
            ),
            handler=sse_handler
        )

        # Initialize HTTP Transport (if implemented)
        # self._init_http_transport()

    async def start(self) -> None:
        """Start the transport system and monitoring"""
        try:
            # Start protocol recovery monitoring
            recovery_task = asyncio.create_task(
                self._protocol_manager.start_recovery_monitoring()
            )
            self._tasks.append(recovery_task)

            # Start fallback monitoring
            fallback_task = asyncio.create_task(
                self._fallback_handler.monitor_protocol_health()
            )
            self._tasks.append(fallback_task)

            if self._config.monitoring_enabled:
                monitoring_task = asyncio.create_task(
                    self._monitoring.start_monitoring()
                )
                self._tasks.append(monitoring_task)

            self._logger.info('MCP Transport System started')
            
            # Wait for all tasks
            await asyncio.gather(*self._tasks)

        except Exception as e:
            self._logger.error(f'Error starting transport system: {str(e)}')
            await self.shutdown()

    async def shutdown(self) -> None:
        """Shutdown the transport system"""
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._logger.info('MCP Transport System shutdown complete')

    async def send_message(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Send message with automatic fallback handling"""
        async def _send(handler: Any, cid: str, msg: Dict[str, Any]) -> bool:
            return await handler.send_message(cid, msg)

        result = await self._fallback_handler.handle_request(_send, client_id, message)
        return bool(result)

    def get_active_protocol(self) -> Optional[ProtocolType]:
        """Get currently active protocol"""
        return self._protocol_manager.get_active_protocol()

    def get_protocol_status(self, protocol: ProtocolType) -> ProtocolStatus:
        """Get status of specific protocol"""
        return self._protocol_manager.get_protocol_status(protocol)

    def is_healthy(self) -> bool:
        """Check if the transport system is healthy"""
        if not self._config.monitoring_enabled:
            return True
        return self._monitoring.is_healthy()