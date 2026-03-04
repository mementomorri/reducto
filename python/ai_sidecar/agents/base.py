"""
Base agent class for all AI agents.

Provides common functionality like LLM routing, MCP client access,
session storage, and plan management.
"""

import uuid
from typing import Dict, Optional, Any

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
