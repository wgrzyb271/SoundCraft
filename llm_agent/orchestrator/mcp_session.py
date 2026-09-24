"""Sesja MCP Orkiestratora jako async context manager (`async with`) — zamyka połączenia, brak zombie.

Orkiestrator używa po stronie MCP tylko `deploy_user_pipeline`; narzędzia agentów (submit_job itd.)
należą do agentów modeli i mają własne połączenia.
"""
from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Any, Protocol

from .deploy import DeployError, DeployFn, make_local_stub_deploy


class McpSession(Protocol):
    async def __aenter__(self) -> "McpSession": ...
    async def __aexit__(self, *exc: Any) -> None: ...
    async def deploy_user_pipeline(self, username: str, temp_audio_path: str, prompt_text: str) -> str: ...


class NullMcpSession:
    """Bez realnego MCP (mock / testy lokalne): deploy = lokalny stub."""

    def __init__(self, user_root: str = "/tmp/orkiestrator_users", deploy: DeployFn | None = None):
        self._deploy = deploy or make_local_stub_deploy(user_root)
        self.closed = False

    async def __aenter__(self) -> "NullMcpSession":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self.closed = True

    async def deploy_user_pipeline(self, username: str, temp_audio_path: str, prompt_text: str) -> str:
        return await self._deploy(username, temp_audio_path, prompt_text)


class StdioMcpSession:
    """Realna sesja MCP przez stdio (SDK `mcp`). NIEPRZETESTOWANA z prawdziwym serwerem WCSS.

    TODO: do ustalenia — komenda serwera MCP i dokładny format wyniku `deploy_user_pipeline`
    (tu zakładamy, że wynik tekstowy = user_dir).
    """

    def __init__(self, command: str, args: list[str] | None = None, env: dict[str, str] | None = None):
        self._params = dict(command=command, args=args or [], env=env)
        self._stack: AsyncExitStack | None = None
        self._session: Any = None

    async def __aenter__(self) -> "StdioMcpSession":
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        self._stack = AsyncExitStack()
        try:
            read, write = await self._stack.enter_async_context(stdio_client(StdioServerParameters(**self._params)))
            self._session = await self._stack.enter_async_context(ClientSession(read, write))
            await self._session.initialize()
        except BaseException:
            await self._stack.aclose()
            raise
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None

    async def deploy_user_pipeline(self, username: str, temp_audio_path: str, prompt_text: str) -> str:
        res = await self._session.call_tool(
            "deploy_user_pipeline",
            {"username": username, "temp_audio_path": temp_audio_path, "prompt_text": prompt_text},
        )
        text = "".join(getattr(c, "text", "") for c in getattr(res, "content", []))
        if getattr(res, "isError", False):
            raise DeployError("MCP_ERROR", text or "deploy_user_pipeline zwrócił błąd")
        return text.strip()
