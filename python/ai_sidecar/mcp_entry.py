"""
MCP entry point for Python sidecar.

Architecture:
- Go runs MCP Server (provides tools: read_file, get_symbols, etc.)
- Python runs MCP Client (calls Go tools)
- Go spawns Python with command type, Python executes and returns results
"""

import argparse
import asyncio
import json
import logging
import sys
import os
from typing import Optional, Dict, Any

from ai_sidecar.mcp import MCPClient, MCPError
from ai_sidecar.agents import (
    AnalyzerAgent,
    DeduplicatorAgent,
    IdiomatizerAgent,
    PatternAgent,
    ValidatorAgent,
)
from ai_sidecar.embeddings import EmbeddingService
from ai_sidecar.llm import LLMRouter
from ai_sidecar.models import (
    AnalyzeRequest,
    AnalyzeResult,
    DeduplicateRequest,
    IdiomatizeRequest,
    PatternRequest,
    RefactorPlan,
    FileInfo,
    Language,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


class MCPSidecar:
    """
    Python sidecar that connects to Go MCP server.
    
    Communication flow:
    1. Go spawns this process with --command and --root args
    2. Python connects MCP client to Go via stdin/stdout
    3. Python executes the requested command using MCP tools
    4. Python prints result JSON to stdout (Go reads this)
    """

    def __init__(self):
        self.mcp: Optional[MCPClient] = None
        self.embedding_service: Optional[EmbeddingService] = None
        self.llm_router: Optional[LLMRouter] = None
        self.analyzer: Optional[AnalyzerAgent] = None
        self.deduplicator: Optional[DeduplicatorAgent] = None
        self.idiomatizer: Optional[IdiomatizerAgent] = None
        self.pattern_agent: Optional[PatternAgent] = None
        self.validator: Optional[ValidatorAgent] = None
        self.root_dir: str = "."
        self._plans: Dict[str, RefactorPlan] = {}

    async def initialize(self, root_dir: str):
        self.root_dir = root_dir
        
        self.mcp = MCPClient()
        await self.mcp.connect()

        init_result = await self.mcp.initialize(root_dir)
        logger.info(f"MCP initialized: {init_result}")

        self.embedding_service = EmbeddingService()
        await self.embedding_service.initialize()

        self.llm_router = LLMRouter()

        self.analyzer = AnalyzerAgent(llm_router=self.llm_router, mcp_client=self.mcp)
        self.deduplicator = DeduplicatorAgent(
            self.embedding_service, llm_router=self.llm_router, mcp_client=self.mcp
        )
        self.idiomatizer = IdiomatizerAgent(llm_router=self.llm_router, mcp_client=self.mcp)
        self.pattern_agent = PatternAgent(llm_router=self.llm_router, mcp_client=self.mcp)
        self.validator = ValidatorAgent(mcp_client=self.mcp)
        self.validator.set_agents(self.deduplicator, self.idiomatizer, self.pattern_agent)

        logger.info("MCPSidecar initialized successfully")

    async def run_command(self, command: str, path: str) -> Dict[str, Any]:
        """Execute a single command and return result."""
        logger.info(f"Running command: {command} on {path}")
        
        try:
            if command == "analyze":
                return await self._analyze(path)
            elif command == "deduplicate":
                return await self._deduplicate(path)
            elif command == "idiomatize":
                return await self._idiomatize(path)
            elif command == "pattern":
                return await self._pattern(path)
            else:
                return {"error": f"Unknown command: {command}"}
        except Exception as e:
            logger.exception(f"Command failed: {e}")
            return {"error": str(e)}

    async def _analyze(self, path: str) -> Dict[str, Any]:
        files_data = await self.mcp.list_files()
        files = [
            FileInfo(path=f["path"], content="", hash=f.get("hash"))
            for f in files_data.get("files", [])
        ]

        request = AnalyzeRequest(path=path, files=files)
        result = await self.analyzer.analyze(request)
        return result.model_dump()

    async def _deduplicate(self, path: str) -> Dict[str, Any]:
        files_data = await self.mcp.list_files()
        files = [
            FileInfo(path=f["path"], content="", hash=f.get("hash"))
            for f in files_data.get("files", [])
        ]

        request = DeduplicateRequest(path=path, files=files, similarity_threshold=0.85)
        plan = await self.deduplicator.find_duplicates(request)
        self._plans[plan.session_id] = plan
        return plan.model_dump()

    async def _idiomatize(self, path: str) -> Dict[str, Any]:
        files_data = await self.mcp.list_files()
        files = [
            FileInfo(path=f["path"], content="", hash=f.get("hash"))
            for f in files_data.get("files", [])
        ]

        request = IdiomatizeRequest(path=path, files=files, language=Language.PYTHON)
        plan = await self.idiomatizer.idiomatize(request)
        self._plans[plan.session_id] = plan
        return plan.model_dump()

    async def _pattern(self, path: str) -> Dict[str, Any]:
        files_data = await self.mcp.list_files()
        files = [
            FileInfo(path=f["path"], content="", hash=f.get("hash"))
            for f in files_data.get("files", [])
        ]

        request = PatternRequest(pattern="", path=path, files=files)
        plan = await self.pattern_agent.apply_pattern(request)
        self._plans[plan.session_id] = plan
        return plan.model_dump()

    async def shutdown(self):
        logger.info("Shutting down MCPSidecar...")

        if self.embedding_service:
            await self.embedding_service.shutdown()

        if self.mcp:
            await self.mcp.shutdown()

        logger.info("Shutdown complete")


async def main():
    parser = argparse.ArgumentParser(description="dehydrator AI Sidecar (MCP mode)")
    parser.add_argument("--root", default=".", help="Root directory")
    parser.add_argument("--command", default="analyze", help="Command to execute")
    args = parser.parse_args()

    sidecar = MCPSidecar()
    result = None
    exit_code = 0
    
    try:
        await sidecar.initialize(args.root)
        result = await sidecar.run_command(args.command, args.root)
        
    except MCPError as e:
        logger.error(f"MCP error: {e}")
        result = {"error": str(e)}
        exit_code = 1
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        result = {"error": str(e)}
        exit_code = 1
    finally:
        await sidecar.shutdown()

    if result:
        print("RESULT:" + json.dumps({"status": "success" if "error" not in result else "error", "data": result}), file=sys.stderr)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
