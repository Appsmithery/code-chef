"""
LangChain Memory Patterns
Provides memory management utilities for agent workflows
"""

from langchain.memory import ConversationBufferMemory, VectorStoreRetrieverMemory
from langchain.vectorstores import Qdrant as LangChainQdrant
from langchain.embeddings.base import Embeddings
from agents._shared.qdrant_client import get_qdrant_client
import os
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class GradientEmbeddings(Embeddings):
    """Gradient AI embeddings for LangChain"""
    
    def __init__(self):
        from agents._shared.gradient_client import get_gradient_client
        self.gradient = get_gradient_client("embeddings")
        self.model = os.getenv("GRADIENT_EMBEDDING_MODEL", "text-embedding-3-large")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents"""
        # TODO: Implement batch embedding with Gradient AI
        return [self.embed_query(text) for text in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query"""
        # TODO: Implement with Gradient AI embedding endpoint
        # For now, return placeholder
        logger.warning("Gradient embeddings not yet implemented")
        return [0.0] * 1536  # Placeholder 1536-dim vector


def create_conversation_memory(
    memory_key: str = "chat_history",
    return_messages: bool = True
) -> ConversationBufferMemory:
    """Create conversation buffer memory for chat history"""
    return ConversationBufferMemory(
        memory_key=memory_key,
        return_messages=return_messages
    )


def create_vector_memory(
    collection_name: str = "agent_memory",
    search_kwargs: Optional[dict] = None
) -> Optional[VectorStoreRetrieverMemory]:
    """Create vector store memory using Qdrant Cloud"""
    qdrant_client = get_qdrant_client()
    
    if not qdrant_client.is_enabled():
        logger.warning("Qdrant Cloud not available, vector memory disabled")
        return None
    
    embeddings = GradientEmbeddings()
    
    vectorstore = LangChainQdrant(
        client=qdrant_client.client,
        collection_name=collection_name,
        embeddings=embeddings
    )
    
    if search_kwargs is None:
        search_kwargs = {"k": 5}
    
    return VectorStoreRetrieverMemory(
        retriever=vectorstore.as_retriever(search_kwargs=search_kwargs)
    )


class HybridMemory:
    """Combines conversation buffer and vector store memory"""
    
    def __init__(self):
        self.buffer_memory = create_conversation_memory()
        self.vector_memory = create_vector_memory()
    
    def save_context(self, inputs: dict, outputs: dict):
        """Save context to both memory types"""
        self.buffer_memory.save_context(inputs, outputs)
        if self.vector_memory:
            self.vector_memory.save_context(inputs, outputs)
    
    def load_memory_variables(self, inputs: dict) -> dict:
        """Load memory variables from both sources"""
        buffer_vars = self.buffer_memory.load_memory_variables(inputs)
        
        if self.vector_memory:
            vector_vars = self.vector_memory.load_memory_variables(inputs)
            # Combine both memory sources
            return {**buffer_vars, **vector_vars}
        
        return buffer_vars
