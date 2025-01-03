import csv
import json
from pathlib import Path

from tools.systemmonitortool import SystemMonitorTool


def test_system_monitor_tool_initialization():
    tool = SystemMonitorTool()
    assert tool.name == 'systemmonitortool'
    assert isinstance(tool.description, str)

def test_get_system_metrics():
    tool = SystemMonitorTool()
    metrics = tool.get_system_metrics()
    
    # Check required fields
    assert 'timestamp' in metrics
    assert 'cpu' in metrics
    assert 'memory' in metrics
    assert 'disk' in metrics
    assert 'network' in metrics

def test_monitor_json_output(tmp_path):
    tool = SystemMonitorTool()
    output_file = tmp_path / 'system_metrics.json'
    
    # Monitor for 2 seconds
    result = tool.monitor(
        output_file=str(output_file),
        interval=1,
        duration=2,
        format='json'
    )
    
    assert output_file.exists()
    assert 'Successfully' in result
    
    # Verify JSON format
    with open(output_file, encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            assert 'timestamp' in data

def test_monitor_csv_output(tmp_path):
    tool = SystemMonitorTool()
    output_file = tmp_path / 'system_metrics.csv'
    
    # Monitor for 2 seconds
    result = tool.monitor(
        output_file=str(output_file),
        interval=1,
        duration=2,
        format='csv'
    )
    
    assert output_file.exists()
    assert 'Successfully' in result
    
    # Verify CSV format
    with open(output_file, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        assert 'timestamp' in headers
        
        for row in reader:
            assert all(field in row for field in headers)

def test_monitor_with_resource_filter():
    tool = SystemMonitorTool()
    output_file = 'test_metrics_filtered.json'
    
    # Monitor only CPU and memory
    result = tool.monitor(
        output_file=output_file,
        interval=1,
        duration=2,
        resources=['cpu', 'memory']
    )
    
    assert 'Successfully' in result
    
    # Verify only requested resources are present
    with open(output_file, encoding='utf-8') as f:
        data = json.loads(f.readline())
        assert set(data.keys()) == {'timestamp', 'cpu', 'memory'}
    
    # Cleanup
    Path(output_file).unlink()