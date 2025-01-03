import hashlib
import json
from typing import Any, Dict, Optional

def generate_content_hash(content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate a unique hash for content and metadata.
    
    This improved version ensures consistent hashing by:
    1. Normalizing content (strip whitespace, lowercase)
    2. Sorting metadata keys
    3. Using a consistent JSON serialization
    """
    # Normalize content
    normalized_content = content.strip().lower()
    
    # Create hash content with normalized content
    hash_content = normalized_content
    
    # Add metadata if present
    if metadata:
        # Filter out timestamp and dynamic fields
        static_metadata = {
            k: v for k, v in metadata.items() 
            if k not in ['timestamp', 'content_hash', 'embedding']
        }
        if static_metadata:
            # Sort keys and use consistent JSON serialization
            hash_content += json.dumps(static_metadata, sort_keys=True, ensure_ascii=True)
    
    # Generate hash
    return hashlib.sha256(hash_content.encode('utf-8')).hexdigest()