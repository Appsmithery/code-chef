"""
Session Manager for Conversational AI

Manages chat sessions with persistent conversation history.
Uses PostgreSQL for session storage and hybrid memory for context.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import asyncpg
import os

logger = logging.getLogger(__name__)


class ChatSession(BaseModel):
    """Chat session with conversation history."""
    session_id: str
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}
    

class SessionManager:
    """
    Manages chat sessions with PostgreSQL persistence.
    
    Features:
    - Session creation and retrieval
    - Message history storage
    - Session TTL and cleanup
    - Context injection for LLM prompts
    """
    
    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        """
        Initialize session manager.
        
        Args:
            db_pool: PostgreSQL connection pool (optional, will create if not provided)
        """
        self.db_pool = db_pool
        self._pool_created = False
    
    async def ensure_pool(self):
        """Ensure database connection pool is available."""
        if self.db_pool is not None:
            return
        
        # Create pool if not provided
        db_host = os.getenv("DB_HOST", "postgres")
        db_port = int(os.getenv("DB_PORT", "5432"))
        db_name = os.getenv("DB_NAME", "devtools")
        db_user = os.getenv("DB_USER", "devtools")
        db_password = os.getenv("DB_PASSWORD", "changeme")
        
        try:
            self.db_pool = await asyncpg.create_pool(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password,
                min_size=2,
                max_size=10
            )
            self._pool_created = True
            logger.info(f"Created database pool: {db_host}:{db_port}/{db_name}")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}", exc_info=True)
            raise
    
    async def close(self):
        """Close database connection pool."""
        if self._pool_created and self.db_pool:
            await self.db_pool.close()
            logger.info("Closed database pool")
    
    async def create_session(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new chat session.
        
        Args:
            user_id: Optional user identifier
            session_id: Optional custom session ID (generates UUID if not provided)
            metadata: Optional session metadata
            
        Returns:
            Session ID
        """
        await self.ensure_pool()
        
        session_id = session_id or f"session-{uuid.uuid4()}"
        now = datetime.utcnow()
        
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO chat_sessions (session_id, user_id, created_at, updated_at, metadata)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (session_id) DO NOTHING
            """, session_id, user_id, now, now, metadata or {})
        
        logger.info(f"Created chat session: {session_id}")
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session metadata.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session dict or None if not found
        """
        await self.ensure_pool()
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT session_id, user_id, created_at, updated_at, metadata
                FROM chat_sessions
                WHERE session_id = $1
            """, session_id)
            
            if not row:
                return None
            
            return dict(row)
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a message to the session history.
        
        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional message metadata
        """
        await self.ensure_pool()
        
        now = datetime.utcnow()
        message_id = f"msg-{uuid.uuid4()}"
        
        async with self.db_pool.acquire() as conn:
            # Insert message
            await conn.execute("""
                INSERT INTO chat_messages (message_id, session_id, role, content, created_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, message_id, session_id, role, content, now, metadata or {})
            
            # Update session timestamp
            await conn.execute("""
                UPDATE chat_sessions
                SET updated_at = $1
                WHERE session_id = $2
            """, now, session_id)
        
        logger.debug(f"Added message to session {session_id}: {role}")
    
    async def load_conversation_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Load conversation history for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to retrieve (most recent)
            
        Returns:
            List of message dicts (oldest to newest)
        """
        await self.ensure_pool()
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT message_id, role, content, created_at, metadata
                FROM chat_messages
                WHERE session_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, session_id, limit)
            
            # Reverse to get chronological order
            messages = [dict(row) for row in reversed(rows)]
            
            return messages
    
    async def cleanup_expired_sessions(self, ttl_hours: int = 24) -> int:
        """
        Delete sessions older than TTL.
        
        Args:
            ttl_hours: Session time-to-live in hours
            
        Returns:
            Number of sessions deleted
        """
        await self.ensure_pool()
        
        cutoff = datetime.utcnow() - timedelta(hours=ttl_hours)
        
        async with self.db_pool.acquire() as conn:
            # Delete old messages
            await conn.execute("""
                DELETE FROM chat_messages
                WHERE session_id IN (
                    SELECT session_id FROM chat_sessions WHERE updated_at < $1
                )
            """, cutoff)
            
            # Delete old sessions
            result = await conn.execute("""
                DELETE FROM chat_sessions
                WHERE updated_at < $1
            """, cutoff)
            
            # Extract count from result
            deleted_count = int(result.split()[-1])
            
            logger.info(f"Cleaned up {deleted_count} expired sessions (TTL: {ttl_hours}h)")
            return deleted_count


# Singleton instance
_session_manager: Optional[SessionManager] = None


def get_session_manager(db_pool: Optional[asyncpg.Pool] = None) -> SessionManager:
    """Get or create session manager singleton."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(db_pool)
    return _session_manager


# SQL Schema for chat sessions (to be added to config/state/schema.sql)
CHAT_SCHEMA = """
-- Chat sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at);

-- Chat messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    message_id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- user, assistant, system
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
"""
