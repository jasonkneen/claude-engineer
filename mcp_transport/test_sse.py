import pytest
import asyncio
from fastapi import FastAPI, Request
from enhanced_sse import EnhancedSSETransport, ConnectionConfig, ConnectionState
from event_filters import EventFilter
from monitoring import MonitoringSystem, MetricType

@pytest.fixture
def sse_transport():
    config = ConnectionConfig(
        max_retries=3,
        retry_delay=100,
        health_check_interval=5,
        connection_timeout=1000
    )
    return EnhancedSSETransport(config)

@pytest.fixture
def monitoring_system():
    return MonitoringSystem(health_check_interval=5)

@pytest.mark.asyncio
async def test_connection_lifecycle(sse_transport):
    client_id = 'test_client'
    
    # Test initial connection
    assert sse_transport.get_connection_state(client_id) == ConnectionState.DISCONNECTED
    
    # Simulate connection
    sse_transport._connection_states[client_id] = ConnectionState.CONNECTED
    assert sse_transport.get_connection_state(client_id) == ConnectionState.CONNECTED
    
    # Test disconnection
    await sse_transport.disconnect(client_id)
    assert sse_transport.get_connection_state(client_id) == ConnectionState.DISCONNECTED

@pytest.mark.asyncio
async def test_event_filtering(sse_transport):
    client_id = 'test_client'
    
    # Create test filters
    topic_filter = EventFilter.create_topic_filter(['test', 'important'])
    pattern_filter = EventFilter.create_pattern_filter(r'urgent|critical')
    combined_filter = EventFilter.combine_filters([topic_filter, pattern_filter])
    
    # Add filter to transport
    sse_transport.add_message_filter(client_id, combined_filter)
    
    # Test message filtering
    test_messages = [
        {'topic': 'test', 'data': 'urgent message'},  # Should pass
        {'topic': 'other', 'data': 'urgent message'},  # Should fail
        {'topic': 'test', 'data': 'normal message'},   # Should fail
    ]
    
    for msg in test_messages:
        filtered = await sse_transport._get_filtered_message(client_id)
        if filtered:
            assert filtered['topic'] in ['test', 'important']
            assert any(word in filtered['data'] for word in ['urgent', 'critical'])

@pytest.mark.asyncio
async def test_monitoring(monitoring_system):
    # Test metric recording
    monitoring_system.record_metric(
        name='connection_count',
        value=1.0,
        metric_type=MetricType.GAUGE,
        labels={'client_id': 'test_client'}
    )
    
    metrics = monitoring_system.get_metrics()
    assert len(metrics) > 0
    assert metrics[0].name == 'connection_count'
    
    # Test health check
    assert monitoring_system.is_healthy() == True
    last_check = monitoring_system.get_last_health_check()
    assert last_check > 0