import time
from typing import Dict, Any, List
from dataclasses import dataclass
import asyncio
import logging
from enum import Enum

class MetricType(Enum):
    COUNTER = 'counter'
    GAUGE = 'gauge'
    HISTOGRAM = 'histogram'

@dataclass
class Metric:
    name: str
    type: MetricType
    value: float
    labels: Dict[str, str]
    timestamp: float

class MonitoringSystem:
    def __init__(self, health_check_interval: int = 30):
        self._metrics: List[Metric] = []
        self._health_check_interval = health_check_interval
        self._logger = logging.getLogger(__name__)
        self._is_healthy = True
        self._last_health_check = time.time()
        
    async def start_monitoring(self):
        while True:
            await self._perform_health_check()
            await asyncio.sleep(self._health_check_interval)
    
    async def _perform_health_check(self):
        try:
            # Implement health check logic here
            self._is_healthy = True
            self._last_health_check = time.time()
        except Exception as e:
            self._is_healthy = False
            self._logger.error(f'Health check failed: {str(e)}')
    
    def record_metric(self, name: str, value: float, metric_type: MetricType, labels: Dict[str, str] = None):
        metric = Metric(
            name=name,
            type=metric_type,
            value=value,
            labels=labels or {},
            timestamp=time.time()
        )
        self._metrics.append(metric)
    
    def get_metrics(self) -> List[Metric]:
        return self._metrics
    
    def is_healthy(self) -> bool:
        return self._is_healthy
    
    def get_last_health_check(self) -> float:
        return self._last_health_check