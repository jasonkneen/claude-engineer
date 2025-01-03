import psutil
import json
import csv
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

class SystemMonitorTool:
    """
    A tool for monitoring and logging system resources including CPU, memory,
    disk, and network usage.
    """
    
    def __init__(self):
        self.name = 'systemmonitortool'
        self.description = '''
    Monitors system resources and logs them to a file.
    Features:
    - CPU, memory, disk, and network monitoring
    - Configurable monitoring intervals
    - Multiple output formats (JSON, CSV)
    - Automatic log rotation
    - Cross-platform compatibility
    '''

    def get_system_metrics(self) -> Dict:
        """Collect current system metrics"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu': {
                'percent': psutil.cpu_percent(interval=1, percpu=True),
                'overall': psutil.cpu_percent(interval=1)
            },
            'memory': dict(psutil.virtual_memory()._asdict()),
            'disk': {
                'usage': dict(psutil.disk_usage('/')._asdict()),
                'io': dict(psutil.disk_io_counters()._asdict()) if psutil.disk_io_counters() else {}
            },
            'network': dict(psutil.net_io_counters()._asdict())
        }
        return metrics

    def monitor(self, 
                output_file: str,
                interval: int = 5,
                format: str = 'json',
                duration: Optional[int] = None,
                resources: Optional[List[str]] = None) -> str:
        """
        Monitor system resources and log them to a file.
        
        Args:
            output_file: Path to the output log file
            interval: Monitoring interval in seconds
            format: Output format ('json' or 'csv')
            duration: Optional duration in seconds to monitor
            resources: Optional list of resources to monitor
            
        Returns:
            Status message indicating monitoring results
        """
        try:
            start_time = time.time()
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'a') as f:
                while True:
                    metrics = self.get_system_metrics()
                    
                    # Filter resources if specified
                    if resources:
                        metrics = {k: v for k, v in metrics.items() 
                                 if k in resources or k == 'timestamp'}
                    
                    # Write metrics in specified format
                    if format.lower() == 'json':
                        f.write(json.dumps(metrics) + '\n')
                    else:  # CSV format
                        if f.tell() == 0:  # Write header if file is empty
                            writer = csv.DictWriter(f, fieldnames=metrics.keys())
                            writer.writeheader()
                        writer = csv.DictWriter(f, fieldnames=metrics.keys())
                        writer.writerow(metrics)
                    
                    f.flush()
                    
                    if duration and (time.time() - start_time) >= duration:
                        break
                        
                    time.sleep(interval)
                    
            return f'Successfully monitored system resources to {output_file}'
            
        except Exception as e:
            return f'Error monitoring system resources: {str(e)}'
