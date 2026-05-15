"""Minimal LSP JSON-RPC client over stdio (Linux language servers)."""

from __future__ import annotations

import json
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from reducto.models import Language
from reducto.repo import detect_language


class LSPError(Exception):
    pass


@dataclass
class Reference:
    uri: str
    path: str
    line: int
    column: int


def _path_to_uri(root: Path, rel: str) -> str:
    return (root / rel).resolve().as_uri()


def _uri_to_path(uri: str) -> str:
    if uri.startswith("file://"):
        return Path(uri.removeprefix("file://")).as_posix()
    return uri


class _LSPClient:
    def __init__(self, cmd: list[str], root: Path):
        self.root = root
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=str(root),
        )
        self._id = 0
        self._lock = threading.Lock()
        self._pending: dict[int, dict[str, Any]] = {}
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self._initialize()

    def _read_loop(self) -> None:
        assert self._proc.stdout
        while True:
            header = {}
            while True:
                line = self._proc.stdout.readline()
                if not line:
                    return
                text = line.decode().strip()
                if not text:
                    break
                if ":" in text:
                    k, v = text.split(":", 1)
                    header[k.strip().lower()] = v.strip()
            length = int(header.get("content-length", 0))
            if length <= 0:
                continue
            body = self._proc.stdout.read(length)
            if not body:
                return
            msg = json.loads(body)
            if "id" in msg and msg["id"] is not None:
                with self._lock:
                    self._pending[int(msg["id"])] = msg

    def _send(self, msg: dict[str, Any]) -> None:
        assert self._proc.stdin
        data = json.dumps(msg).encode()
        self._proc.stdin.write(f"Content-Length: {len(data)}\r\n\r\n".encode())
        self._proc.stdin.write(data)
        self._proc.stdin.flush()

    def _request(self, method: str, params: Any) -> Any:
        with self._lock:
            self._id += 1
            rid = self._id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        for _ in range(200):
            with self._lock:
                resp = self._pending.pop(rid, None)
            if resp is not None:
                if "error" in resp:
                    raise LSPError(resp["error"].get("message", "LSP error"))
                return resp.get("result")
            threading.Event().wait(0.05)
        raise LSPError(f"LSP timeout: {method}")

    def _notify(self, method: str, params: Any = None) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def _initialize(self) -> None:
        root_uri = self.root.as_uri()
        self._request(
            "initialize",
            {
                "processId": None,
                "rootUri": root_uri,
                "capabilities": {},
            },
        )
        self._notify("initialized", {})

    def find_references(self, rel_path: str, line: int, character: int = 0) -> list[Reference]:
        uri = _path_to_uri(self.root, rel_path)
        result = self._request(
            "textDocument/references",
            {
                "textDocument": {"uri": uri},
                "position": {"line": max(0, line - 1), "character": character},
                "context": {"includeDeclaration": True},
            },
        )
        if not result:
            return []
        refs: list[Reference] = []
        for loc in result:
            loc_uri = loc.get("uri", "")
            start = loc.get("range", {}).get("start", {})
            refs.append(
                Reference(
                    uri=loc_uri,
                    path=_uri_to_path(loc_uri),
                    line=int(start.get("line", 0)) + 1,
                    column=int(start.get("character", 0)),
                )
            )
        return refs

    def shutdown(self) -> None:
        try:
            self._request("shutdown", None)
            self._notify("exit")
        except LSPError:
            pass
        if self._proc.poll() is None:
            self._proc.terminate()


def _server_cmd(lang: Language) -> list[str] | None:
    if lang == Language.PYTHON:
        for cmd in (["pyright-langserver", "--stdio"], ["pylsp"]):
            if shutil.which(cmd[0]):
                return cmd
        return None
    if lang == Language.GO:
        if shutil.which("gopls"):
            return ["gopls", "serve"]
        return None
    if lang in (Language.TYPESCRIPT, Language.JAVASCRIPT):
        if shutil.which("typescript-language-server"):
            return ["typescript-language-server", "--stdio"]
        return None
    return None


class LSPManager:
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self._clients: dict[Language, _LSPClient] = {}

    def _client(self, lang: Language) -> _LSPClient | None:
        if lang in self._clients:
            return self._clients[lang]
        cmd = _server_cmd(lang)
        if not cmd:
            return None
        try:
            client = _LSPClient(cmd, self.root)
            self._clients[lang] = client
            return client
        except OSError as e:
            raise LSPError(str(e)) from e

    def find_references(self, path: str, line: int, character: int = 0) -> list[Reference]:
        lang = detect_language(path)
        client = self._client(lang)
        if client is None:
            raise LSPError(f"no LSP server on PATH for {lang.value}")
        return client.find_references(path, line, character)

    def shutdown(self) -> None:
        for c in self._clients.values():
            c.shutdown()
        self._clients.clear()
