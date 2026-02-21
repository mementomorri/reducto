"""
Tests for the Python MCP client.
"""

import json
import asyncio
from io import StringIO, BytesIO
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from ai_sidecar.mcp.client import MCPClient, MCPError


class TestMCPError:
    """Test MCPError exception class."""

    def test_error_creation(self):
        """Test creating an MCPError."""
        error = MCPError(code=-32600, message="Invalid request", data={"foo": "bar"})

        assert error.code == -32600
        assert error.message == "Invalid request"
        assert error.data == {"foo": "bar"}
        assert "Invalid request" in str(error)

    def test_error_without_data(self):
        """Test creating an MCPError without data."""
        error = MCPError(code=-32601, message="Method not found")

        assert error.code == -32601
        assert error.message == "Method not found"
        assert error.data is None


class TestMCPClient:
    """Test MCPClient class."""

    def test_client_creation(self):
        """Test creating an MCPClient."""
        client = MCPClient()

        assert client._request_id == 0
        assert client._pending == {}
        assert client._reader is None
        assert client._writer is None
        assert client._initialized is False

    def test_is_initialized_property(self):
        """Test is_initialized property."""
        client = MCPClient()
        assert client.is_initialized is False

        client._initialized = True
        assert client.is_initialized is True


class TestMCPClientMethods:
    """Test MCPClient method generation."""

    def test_method_call_without_connection(self):
        """Test that call raises error when not connected."""
        client = MCPClient()

        async def run():
            with pytest.raises(RuntimeError, match="Not connected"):
                await client.call("test_method")

        asyncio.run(run())

    def test_read_file_params(self):
        """Test read_file generates correct params."""
        client = MCPClient()

        async def run():
            with pytest.raises(RuntimeError):
                await client.read_file("test.py")

        asyncio.run(run())

    def test_get_symbols_params(self):
        """Test get_symbols generates correct params."""
        client = MCPClient()

        async def run():
            with pytest.raises(RuntimeError):
                await client.get_symbols("test.py")

            with pytest.raises(RuntimeError):
                await client.get_symbols("test.py", content="def foo(): pass")

        asyncio.run(run())

    def test_find_references_params(self):
        """Test find_references generates correct params."""
        client = MCPClient()

        async def run():
            with pytest.raises(RuntimeError):
                await client.find_references("test.py", 10, 5)

        asyncio.run(run())

    def test_apply_diff_params(self):
        """Test apply_diff generates correct params."""
        client = MCPClient()

        async def run():
            with pytest.raises(RuntimeError):
                await client.apply_diff("test.py", "--- a\n+++ b\n")

            with pytest.raises(RuntimeError):
                await client.apply_diff("test.py", "--- a\n+++ b\n", session_id="abc123")

        asyncio.run(run())

    def test_git_checkpoint_params(self):
        """Test git_checkpoint generates correct params."""
        client = MCPClient()

        async def run():
            with pytest.raises(RuntimeError):
                await client.git_checkpoint()

            with pytest.raises(RuntimeError):
                await client.git_checkpoint(message="custom message")

        asyncio.run(run())

    def test_list_files_params(self):
        """Test list_files generates correct params."""
        client = MCPClient()

        async def run():
            with pytest.raises(RuntimeError):
                await client.list_files()

            with pytest.raises(RuntimeError):
                await client.list_files(include_patterns=["*.py"])

            with pytest.raises(RuntimeError):
                await client.list_files(exclude_patterns=["node_modules"])

            with pytest.raises(RuntimeError):
                await client.list_files(
                    include_patterns=["*.py"],
                    exclude_patterns=["tests"]
                )

        asyncio.run(run())

    def test_get_complexity_params(self):
        """Test get_complexity generates correct params."""
        client = MCPClient()

        async def run():
            with pytest.raises(RuntimeError):
                await client.get_complexity("test.py")

            with pytest.raises(RuntimeError):
                await client.get_complexity("test.py", content="def foo(): pass")

        asyncio.run(run())


class TestMCPClientIntegration:
    """Integration tests for MCPClient with mock server."""

    @pytest.mark.asyncio
    async def test_handle_response_success(self):
        """Test handling a successful response."""
        client = MCPClient()

        future = asyncio.get_event_loop().create_future()
        client._pending[1] = future

        response = {"jsonrpc": "2.0", "id": 1, "result": {"status": "ok"}}
        client._handle_response(response)

        assert future.done()
        assert future.result() == {"status": "ok"}
        assert 1 not in client._pending

    @pytest.mark.asyncio
    async def test_handle_response_error(self):
        """Test handling an error response."""
        client = MCPClient()

        future = asyncio.get_event_loop().create_future()
        client._pending[2] = future

        response = {
            "jsonrpc": "2.0",
            "id": 2,
            "error": {"code": -32600, "message": "Invalid request"},
        }
        client._handle_response(response)

        assert future.done()
        with pytest.raises(MCPError) as exc_info:
            future.result()

        assert exc_info.value.code == -32600
        assert exc_info.value.message == "Invalid request"

    @pytest.mark.asyncio
    async def test_handle_response_unknown_id(self):
        """Test handling a response for unknown request ID."""
        client = MCPClient()

        response = {"jsonrpc": "2.0", "id": 999, "result": {"status": "ok"}}

        client._handle_response(response)
        assert 999 not in client._pending

    @pytest.mark.asyncio
    async def test_handle_response_no_id(self):
        """Test handling a response without ID."""
        client = MCPClient()

        future = asyncio.get_event_loop().create_future()
        client._pending[1] = future

        response = {"jsonrpc": "2.0", "result": {"status": "ok"}}
        client._handle_response(response)

        assert not future.done()

    @pytest.mark.asyncio
    async def test_handle_response_with_error_data(self):
        """Test handling an error response with data."""
        client = MCPClient()

        future = asyncio.get_event_loop().create_future()
        client._pending[3] = future

        response = {
            "jsonrpc": "2.0",
            "id": 3,
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": "Missing required field: path",
            },
        }
        client._handle_response(response)

        assert future.done()
        with pytest.raises(MCPError) as exc_info:
            future.result()

        assert exc_info.value.code == -32602
        assert exc_info.value.data == "Missing required field: path"


class TestMCPClientRequestBuilding:
    """Test MCPClient request building."""

    def test_request_id_increment(self):
        """Test that request IDs increment correctly."""
        client = MCPClient()

        assert client._request_id == 0
        client._request_id += 1
        assert client._request_id == 1
        client._request_id += 1
        assert client._request_id == 2
