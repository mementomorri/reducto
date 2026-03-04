"""
Session persistence for refactoring plans.

Stores plans to disk so they survive sidecar restarts and can be resumed.
"""

import json
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from ai_sidecar.models import RefactorPlan

logger = logging.getLogger(__name__)


class SessionInfo:
    """Metadata about a stored session."""
    
    def __init__(
        self,
        session_id: str,
        created_at: datetime,
        command_type: str,
        file_count: int,
        change_count: int,
        description: str = "",
    ):
        self.session_id = session_id
        self.created_at = created_at
        self.command_type = command_type
        self.file_count = file_count
        self.change_count = change_count
        self.description = description
    
    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "command_type": self.command_type,
            "file_count": self.file_count,
            "change_count": self.change_count,
            "description": self.description,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SessionInfo":
        return cls(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            command_type=data["command_type"],
            file_count=data["file_count"],
            change_count=data["change_count"],
            description=data.get("description", ""),
        )
    
    def __repr__(self) -> str:
        return f"SessionInfo({self.session_id}, {self.command_type}, {self.change_count} changes)"


class SessionStore:
    """Persistent storage for refactoring plans."""
    
    def __init__(self, storage_dir: str = ".reducto/sessions"):
        self.storage_dir = Path(storage_dir)
        self._cache: Dict[str, RefactorPlan] = {}
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self):
        """Create storage directory if it doesn't exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Session storage directory: {self.storage_dir}")
    
    def _get_session_path(self, session_id: str) -> Path:
        """Get the file path for a session."""
        return self.storage_dir / f"{session_id}.json"
    
    def save_plan(self, plan: RefactorPlan, command_type: str = "unknown") -> None:
        """
        Save a refactoring plan to disk.
        
        Args:
            plan: The RefactorPlan to save
            command_type: Type of command that generated this plan 
                         (deduplicate, idiomatize, pattern)
        """
        session_path = self._get_session_path(plan.session_id)
        
        # Create metadata
        metadata = {
            "version": 1,
            "created_at": plan.created_at.isoformat() if plan.created_at else datetime.now().isoformat(),
            "command_type": command_type,
            "file_count": len(set(c.path for c in plan.changes)),
            "change_count": len(plan.changes),
            "description": plan.description[:200] if plan.description else "",
        }
        
        # Serialize plan
        data = {
            "metadata": metadata,
            "plan": plan.model_dump(mode='json'),
        }
        
        # Write to file
        try:
            with open(session_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Update cache
            self._cache[plan.session_id] = plan
            
            logger.info(f"Saved session {plan.session_id} ({len(plan.changes)} changes)")
        except Exception as e:
            logger.error(f"Failed to save session {plan.session_id}: {e}")
            raise
    
    def load_plan(self, session_id: str) -> Optional[RefactorPlan]:
        """
        Load a refactoring plan from disk.
        
        Args:
            session_id: The session ID to load
            
        Returns:
            The RefactorPlan if found, None otherwise
        """
        # Check cache first
        if session_id in self._cache:
            logger.debug(f"Loading session {session_id} from cache")
            return self._cache[session_id]
        
        session_path = self._get_session_path(session_id)
        
        if not session_path.exists():
            logger.warning(f"Session {session_id} not found")
            return None
        
        try:
            with open(session_path, 'r') as f:
                data = json.load(f)
            
            plan_data = data.get("plan")
            if not plan_data:
                logger.error(f"Invalid session file {session_id}: no plan data")
                return None
            
            plan = RefactorPlan.model_validate(plan_data)
            self._cache[session_id] = plan
            
            logger.info(f"Loaded session {session_id} ({len(plan.changes)} changes)")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None
    
    def list_sessions(self) -> List[SessionInfo]:
        """
        List all stored sessions.
        
        Returns:
            List of SessionInfo objects, sorted by created_at (newest first)
        """
        sessions = []
        
        for session_path in self.storage_dir.glob("*.json"):
            try:
                with open(session_path, 'r') as f:
                    data = json.load(f)
                
                metadata = data.get("metadata", {})
                if not metadata:
                    continue
                
                info = SessionInfo.from_dict(metadata)
                sessions.append(info)
                
            except Exception as e:
                logger.warning(f"Failed to read session {session_path}: {e}")
        
        # Sort by created_at, newest first
        sessions.sort(key=lambda s: s.created_at, reverse=True)
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from storage.
        
        Args:
            session_id: The session ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        session_path = self._get_session_path(session_id)
        
        if not session_path.exists():
            return False
        
        try:
            session_path.unlink()
            self._cache.pop(session_id, None)
            logger.info(f"Deleted session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    def cleanup_old_sessions(self, max_age_days: int = 7) -> int:
        """
        Delete sessions older than max_age_days.
        
        Args:
            max_age_days: Maximum age in days (default: 7)
            
        Returns:
            Number of sessions deleted
        """
        cutoff = datetime.now() - timedelta(days=max_age_days)
        deleted = 0
        
        for session_path in self.storage_dir.glob("*.json"):
            try:
                with open(session_path, 'r') as f:
                    data = json.load(f)
                
                metadata = data.get("metadata", {})
                created_at_str = metadata.get("created_at")
                
                if not created_at_str:
                    continue
                
                created_at = datetime.fromisoformat(created_at_str)
                
                if created_at < cutoff:
                    session_path.unlink()
                    session_id = metadata.get("session_id", "unknown")
                    self._cache.pop(session_id, None)
                    deleted += 1
                    logger.debug(f"Deleted old session {session_id}")
                    
            except Exception as e:
                logger.warning(f"Failed to process session {session_path}: {e}")
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old sessions")
        
        return deleted
    
    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """
        Get metadata for a session without loading the full plan.
        
        Args:
            session_id: The session ID
            
        Returns:
            SessionInfo if found, None otherwise
        """
        session_path = self._get_session_path(session_id)
        
        if not session_path.exists():
            return None
        
        try:
            with open(session_path, 'r') as f:
                data = json.load(f)
            
            metadata = data.get("metadata", {})
            if not metadata:
                return None
            
            return SessionInfo.from_dict(metadata)
            
        except Exception as e:
            logger.error(f"Failed to read session info {session_id}: {e}")
            return None
    
    def clear_cache(self):
        """Clear the in-memory cache."""
        self._cache.clear()
        logger.debug("Session cache cleared")
