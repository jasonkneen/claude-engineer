from typing import Dict, Any, Optional, List
import re

class EventFilter:
    @staticmethod
    def create_topic_filter(topics: List[str]):
        def filter_func(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            if 'topic' in message and message['topic'] in topics:
                return message
            return None
        return filter_func
    
    @staticmethod
    def create_pattern_filter(pattern: str):
        compiled_pattern = re.compile(pattern)
        def filter_func(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            if 'data' in message and isinstance(message['data'], str):
                if compiled_pattern.search(message['data']):
                    return message
            return None
        return filter_func
    
    @staticmethod
    def create_type_filter(allowed_types: List[str]):
        def filter_func(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            if 'type' in message and message['type'] in allowed_types:
                return message
            return None
        return filter_func
    
    @staticmethod
    def combine_filters(filters: List[callable]):
        def combined_filter(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            for filter_func in filters:
                message = filter_func(message)
                if message is None:
                    return None
            return message
        return combined_filter