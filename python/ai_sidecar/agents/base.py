"""
Base agent class for all AI agents.

Provides common functionality like LLM routing, MCP client access,
session storage, and plan management.
"""

import uuid
from typing import Dict, Optional, Any, List

from ai_sidecar.models import RefactorPlan
from ai_sidecar.session import SessionStore


class BaseAgent:
    """Base class for all AI agents."""
    
    def __init__(
        self,
        llm_router=None,
        mcp_client=None,
        session_store: Optional[SessionStore] = None,
    ):
        """
        Initialize base agent.
        
        Args:
            llm_router: LLM router for model selection
            mcp_client: MCP client for tool access
            session_store: Session storage for persistence
        """
        self.llm = llm_router
        self.mcp = mcp_client
        self.session_store = session_store or SessionStore()
        self._session_plans: Dict[str, RefactorPlan] = {}
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return str(uuid.uuid4())
    
    def _save_plan(self, plan: RefactorPlan, command_type: str) -> None:
        """
        Save a plan to both memory and disk.
        
        Args:
            plan: The refactoring plan to save
            command_type: Type of command that generated the plan
        """
        self._session_plans[plan.session_id] = plan
        self.session_store.save_plan(plan, command_type=command_type)
    
    def get_plan(self, session_id: str) -> Optional[RefactorPlan]:
        """
        Get a stored plan by session ID.
        
        Args:
            session_id: The session ID to look up
            
        Returns:
            The RefactorPlan if found, None otherwise
        """
        # Check memory first (faster)
        if session_id in self._session_plans:
            return self._session_plans[session_id]
        
        # Fall back to disk
        return self.session_store.load_plan(session_id)

    def _get_file_content_and_path(self, file) -> tuple[str, str]:
        """
        Extract content and path from a file object (supports both dict and object formats).
        
        Args:
            file: Either a dict with 'content' and 'path' keys, or an object with those attributes
            
        Returns:
            Tuple of (content, path)
        """
        if hasattr(file, 'content'):
            return file.content, file.path
        return file["content"], file["path"]

    def _get_files_content_and_paths(self, files) -> List[tuple[str, str]]:
        """
        Extract content and path from a list of file objects.
        
        Args:
            files: List of files (either dicts or objects)
            
        Returns:
            List of tuples (content, path)
        """
        return [self._get_file_content_and_path(f) for f in files]
