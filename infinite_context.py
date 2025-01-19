import numpy as np
from typing import List, Dict, Any
import json
from transformers import AutoTokenizer, AutoModel
import torch
import faiss
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ContextBlock:
    timestamp: datetime
    content: Dict[str, Any]
    embedding: np.ndarray = None

class InfiniteContext:
    def __init__(self, model_name: str = "sentence-transformers/all-mpnet-base-v2", 
                 max_blocks: int = 1000,
                 similarity_threshold: float = 0.7):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.eval()
        
        self.max_blocks = max_blocks
        self.similarity_threshold = similarity_threshold
        self.context_blocks: List[ContextBlock] = []
        
        # Initialize FAISS index
        self.embedding_dim = self.model.config.hidden_size
        self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product for cosine similarity
        
    def _get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text using the model"""
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
        # Use mean pooling of last hidden state
        embedding = outputs.last_hidden_state.mean(dim=1).numpy()
        # Normalize for cosine similarity
        embedding = embedding / np.linalg.norm(embedding)
        return embedding[0]  # Return the first (and only) embedding
        
    def _compress_blocks(self):
        """Compress context by merging similar blocks"""
        if len(self.context_blocks) <= self.max_blocks:
            return
            
        # Find similar blocks using FAISS
        embeddings = np.vstack([block.embedding for block in self.context_blocks])
        D, I = self.index.search(embeddings, 2)  # Find closest neighbor for each block
        
        # Track blocks to merge
        merged = set()
        new_blocks = []
        
        for i, (distances, indices) in enumerate(zip(D, I)):
            if i in merged:
                continue
                
            # Skip self-similarity (first result is always the same block)
            similarity = distances[1]
            neighbor_idx = indices[1]
            
            # If similarity is above threshold and neighbor hasn't been merged
            if similarity > self.similarity_threshold and neighbor_idx not in merged:
                # Merge blocks
                block1 = self.context_blocks[i]
                block2 = self.context_blocks[neighbor_idx]
                
                # Combine content (assuming dict structure)
                merged_content = {
                    "role": block1.content["role"],
                    "content": self._merge_content(block1.content["content"], 
                                                  block2.content["content"])
                }
                
                # Create new block with averaged embedding
                merged_embedding = (block1.embedding + block2.embedding) / 2
                merged_embedding = merged_embedding / np.linalg.norm(merged_embedding)
                
                new_block = ContextBlock(
                    timestamp=max(block1.timestamp, block2.timestamp),
                    content=merged_content,
                    embedding=merged_embedding
                )
                
                new_blocks.append(new_block)
                merged.add(i)
                merged.add(neighbor_idx)
            elif i not in merged:
                new_blocks.append(self.context_blocks[i])
        
        # Update blocks and index
        self.context_blocks = new_blocks
        self._rebuild_index()
        
    def _merge_content(self, content1: Any, content2: Any) -> Any:
        """Merge two content blocks based on their type"""
        if isinstance(content1, str) and isinstance(content2, str):
            return f"{content1}\n{content2}"
        elif isinstance(content1, list) and isinstance(content2, list):
            return content1 + content2
        else:
            # For other types, just concatenate as strings
            return f"{content1}\n{content2}"
            
    def _rebuild_index(self):
        """Rebuild FAISS index with current blocks"""
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        if self.context_blocks:
            embeddings = np.vstack([block.embedding for block in self.context_blocks])
            self.index.add(embeddings)
            
    def add_context(self, content: Dict[str, Any]):
        """Add new context block"""
        # Convert content to string for embedding
        if isinstance(content["content"], list):
            text_content = " ".join(str(item) for item in content["content"])
        else:
            text_content = str(content["content"])
            
        embedding = self._get_embedding(text_content)
        
        block = ContextBlock(
            timestamp=datetime.now(),
            content=content,
            embedding=embedding
        )
        
        self.context_blocks.append(block)
        
        # Add to index
        self.index.add(embedding.reshape(1, -1))
        
        # Compress if needed
        self._compress_blocks()
        
    def get_relevant_context(self, query: str, max_blocks: int = 5) -> List[Dict[str, Any]]:
        """Get most relevant context blocks for a query"""
        query_embedding = self._get_embedding(query)
        
        # Search for similar blocks
        D, I = self.index.search(query_embedding.reshape(1, -1), min(max_blocks, len(self.context_blocks)))
        
        # Return relevant blocks
        relevant_blocks = []
        for idx in I[0]:
            block = self.context_blocks[idx]
            relevant_blocks.append(block.content)
            
        return relevant_blocks
        
    def clear(self):
        """Clear all context"""
        self.context_blocks = []
        self._rebuild_index()
