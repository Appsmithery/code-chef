"""
LangChain Memory Patterns
Provides memory management utilities for agent workflows using DO Gradient AI embeddings
"""

from langchain.memory import ConversationBufferMemory, VectorStoreRetrieverMemory
from langchain_qdrant import QdrantVectorStore
from agents._shared.qdrant_client import get_qdrant_client
from agents._shared.langchain_gradient import gradient_embeddings
import logging
from typing import Optional

logger = logging.getLogger(__name__)


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
    """
    Create vector store memory using Qdrant Cloud + DO Gradient AI embeddings
    """
    qdrant_client = get_qdrant_client()
    
    if not qdrant_client.is_enabled():
        logger.warning("Qdrant Cloud not available, vector memory disabled")
        return None
    
    if not gradient_embeddings:
        logger.warning("Gradient embeddings not available, vector memory disabled")
        return None
    
    # Use unified embeddings from langchain_gradient (DO Gradient AI)
    vectorstore = QdrantVectorStore(
        client=qdrant_client.client,
        collection_name=collection_name,
        embedding=gradient_embeddings
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
