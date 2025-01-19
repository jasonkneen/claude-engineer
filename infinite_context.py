import numpy as np
from typing import List, Dict, Any
import json
from sklearn.feature_extraction.text import TfidfVectorizer
import faiss
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ContextBlock:
    timestamp: datetime
    content: Dict[str, Any]
    embedding: np.ndarray = None


class InfiniteContext:

    def __init__(self, max_blocks: int = 1000, similarity_threshold: float = 0.7):
        print("\nInitializing TF-IDF vectorizer")
        self.vectorizer = TfidfVectorizer()
        self.max_blocks = max_blocks
        self.similarity_threshold = similarity_threshold
        self.context_blocks: List[ContextBlock] = []

        # We'll set embedding_dim after first vectorization
        self.embedding_dim = None
        self.index = None

    def _get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text using TF-IDF"""
        print(f"\n_get_embedding called with text: {text[:50]}...")

        # If this is our first text, fit the vectorizer and initialize FAISS
        if self.embedding_dim is None:
            vectors = self.vectorizer.fit_transform([text])
            self.embedding_dim = vectors.shape[1]
            print(f"Initialized vectorizer with dimension: {self.embedding_dim}")
            self.index = faiss.IndexFlatIP(self.embedding_dim)
        else:
            vectors = self.vectorizer.transform([text])

        # Convert sparse matrix to dense numpy array
        embedding = vectors.toarray()[0]
        # Normalize for cosine similarity
        if np.linalg.norm(embedding) > 0:
            embedding = embedding / np.linalg.norm(embedding)

        print("Embedding generated and normalized")
        return embedding

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

            # Get all similarities except self-similarity
            similarities = distances[1:]  # Skip first one (self-similarity)
            neighbor_indices = indices[1:]  # Skip first one (self)

            # Find most similar neighbor that hasn't been merged
            max_sim = -1
            best_neighbor = None
            for sim, n_idx in zip(similarities, neighbor_indices):
                if sim > max_sim and n_idx not in merged:
                    max_sim = sim
                    best_neighbor = n_idx

            # If we found a similar enough neighbor
            if max_sim > self.similarity_threshold and best_neighbor is not None:
                neighbor_idx = best_neighbor
                # Merge blocks
                block1 = self.context_blocks[i]
                block2 = self.context_blocks[neighbor_idx]

                # Combine content (assuming dict structure)
                merged_content = {
                    "role": block1.content["role"],
                    "content": self._merge_content(
                        block1.content["content"], block2.content["content"]
                    ),
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
        print(f"\nAdding new context block...")
        # Convert content to string for embedding
        if isinstance(content["content"], list):
            text_content = " ".join(str(item) for item in content["content"])
        else:
            text_content = str(content["content"])
        print(f"Content text: {text_content[:50]}...")

        print("Generating embedding...")
        embedding = self._get_embedding(text_content)
        print("Embedding generated")

        block = ContextBlock(
            timestamp=datetime.now(),
            content=content,
            embedding=embedding
        )

        self.context_blocks.append(block)
        print(f"Block added, total blocks: {len(self.context_blocks)}")

        # Add to index
        print("Updating FAISS index...")
        self.index.add(embedding.reshape(1, -1))
        print(f"Index updated, total vectors: {self.index.ntotal}")

        # Compress if needed
        if len(self.context_blocks) > self.max_blocks:
            print("Running block compression...")
            self._compress_blocks()
            print(f"Compression complete, blocks after: {len(self.context_blocks)}")

    def get_relevant_context(self, query: str, max_blocks: int = 5) -> List[Dict[str, Any]]:
        """Get most relevant context blocks for a query"""
        print(f"\nGenerating embedding for query: {query}")
        query_embedding = self._get_embedding(query)
        print("Query embedding generated")

        print(f"Searching through {len(self.context_blocks)} blocks")
        # Search for similar blocks
        D, I = self.index.search(query_embedding.reshape(1, -1), min(max_blocks, len(self.context_blocks)))
        print(f"Search complete, found {len(I[0])} matches")

        # Return relevant blocks
        relevant_blocks = []
        for idx in I[0]:
            block = self.context_blocks[idx]
            relevant_blocks.append(block.content)
            print(f"Added block: {block.content.get('content', '')[:50]}...")

        return relevant_blocks

    def clear(self):
        """Clear all context"""
        self.context_blocks = []
        self._rebuild_index()
