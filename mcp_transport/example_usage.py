import asyncio
from mcp_transport_system import MCPTransportSystem, TransportConfig
from enhanced_sse import ConnectionConfig
from fallback_handler import FallbackConfig, FallbackStrategy
from protocol_manager import ProtocolType

async def main():
    # Configure the transport system
    config = TransportConfig(
        sse_config=ConnectionConfig(
            max_retries=3,
            retry_delay=1000,
            health_check_interval=30,
            connection_timeout=5000
        ),
        fallback_config=FallbackConfig(
            strategy=FallbackStrategy.SEQUENTIAL,
            retry_interval=5,
            max_retries=3,
            timeout=10
        ),
        monitoring_enabled=True,
        health_check_interval=30
    )

    # Create and start the transport system
    transport = MCPTransportSystem(config)
    
    try:
        # Start the system in the background
        system_task = asyncio.create_task(transport.start())
        
        # Example usage
        client_id = 'test_client'
        message = {
            'type': 'notification',
            'data': 'Test message',
            'priority': 'high'
        }
        
        # Send a message
        success = await transport.send_message(client_id, message)
        print(f'Message sent: {success}')
        
        # Check protocol status
        active_protocol = transport.get_active_protocol()
        print(f'Active protocol: {active_protocol}')
        
        if active_protocol:
            status = transport.get_protocol_status(active_protocol)
            print(f'Protocol status: {status}')
        
        # Check system health
        is_healthy = transport.is_healthy()
        print(f'System healthy: {is_healthy}')
        
        # Keep the system running for a while
        await asyncio.sleep(60)
        
    except KeyboardInterrupt:
        print('Shutting down...')
    finally:
        # Cleanup
        await transport.shutdown()

if __name__ == '__main__':
    asyncio.run(main())