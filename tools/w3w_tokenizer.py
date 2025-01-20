import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import re
import zlib
import json

@dataclass
class TokenBlock:
    tokens: List[str]
    w3w: str
    embedding: Optional[np.ndarray] = None
    
    def __post_init__(self):
        if self.embedding is None:
            self.embedding = np.zeros(768)  # Default embedding size

class VocabularyManager:
    def __init__(self, vocab_size: int = 10000):
        self.vocab_size = vocab_size
        self.token_to_id: Dict[str, int] = {}
        self.id_to_token: Dict[int, str] = {}
        self.frequency: Dict[str, int] = defaultdict(int)
        
    def add_token(self, token: str) -> int:
        if token not in self.token_to_id:
            token_id = len(self.token_to_id)
            if token_id < self.vocab_size:
                self.token_to_id[token] = token_id
                self.id_to_token[token_id] = token
        self.frequency[token] += 1
        return self.token_to_id.get(token, -1)
        
    def get_token(self, token_id: int) -> Optional[str]:
        return self.id_to_token.get(token_id)

class W3WTokenizer:
    def __init__(self, 
                block_size: int = 64,
                vocab_size: int = 10000,
                compression_level: int = 6):
        self.block_size = block_size
        self.compression_level = compression_level
        self.vocabulary = VocabularyManager(vocab_size)
        self.blocks: Dict[str, TokenBlock] = {}
        
    def tokenize(self, text: str) -> List[str]:
        """Convert text to basic tokens."""
        return re.findall(r'\b\w+\b|[^\w\s]', text)
        
    def text_to_w3w(self, text: str) -> List[str]:
        """Convert text to W3W format."""
        tokens = self.tokenize(text)
        w3w_blocks = []
        
        for i in range(0, len(tokens), self.block_size):
            block = tokens[i:i + self.block_size]
            block_key = self._generate_block_key(block)
            if block_key not in self.blocks:
                w3w = self._generate_w3w(block)
                self.blocks[block_key] = TokenBlock(
                    tokens=block,
                    w3w=w3w,
                    embedding=self._compute_embedding(block)
                )
            w3w_blocks.append(self.blocks[block_key].w3w)
            
        return w3w_blocks
        
    def w3w_to_text(self, w3w_blocks: List[str]) -> str:
        """Convert W3W format back to text."""
        result = []
        for w3w in w3w_blocks:
            block = next((b for b in self.blocks.values() if b.w3w == w3w), None)
            if block:
                result.extend(block.tokens)
        return ' '.join(result)
        
    def compress_tokens(self, tokens: List[str]) -> bytes:
        """Compress token sequence."""
        token_ids = [self.vocabulary.add_token(t) for t in tokens]
        data = json.dumps(token_ids).encode('utf-8')
        return zlib.compress(data, self.compression_level)
        
    def decompress_tokens(self, compressed: bytes) -> List[str]:
        """Decompress token sequence."""
        data = zlib.decompress(compressed)
        token_ids = json.loads(data.decode('utf-8'))
        return [self.vocabulary.get_token(tid) for tid in token_ids]
        
    def semantic_search(self, query: str, top_k: int = 5) -> List[TokenBlock]:
        """Search for semantically similar blocks."""
        query_embedding = self._compute_embedding(self.tokenize(query))
        scores = []
        
        for block in self.blocks.values():
            similarity = self._compute_similarity(query_embedding, block.embedding)
            scores.append((similarity, block))
            
        return [block for _, block in sorted(scores, reverse=True)[:top_k]]
        
    def _generate_block_key(self, tokens: List[str]) -> str:
        """Generate unique key for a token block."""
        return '_'.join(tokens)
        
    def _generate_w3w(self, tokens: List[str]) -> str:
        """Generate W3W identifier for a block."""
        # Simplified W3W generation - in practice would use more sophisticated algorithm
        block_hash = hash(''.join(tokens)) % (1000**3)
        words = ['word1', 'word2', 'word3']  # Would use actual word list
        return '.'.join([words[i] for i in [(block_hash//(1000**i))%1000 for i in range(3)]])
        
    def _compute_embedding(self, tokens: List[str]) -> np.ndarray:
        """Compute embedding for tokens."""
        # Simplified embedding - would use proper embedding model in practice
        embedding = np.zeros(768)
        for i, token in enumerate(tokens):
            embedding[i % 768] += hash(token) % 100
        return embedding / np.linalg.norm(embedding)
        
    def _compute_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity between embeddings."""
        return float(np.dot(emb1, emb2))

