from __future__ import annotations

import unittest

import httpx

from llm_agent.orchestrator.callback import notify_backend
from llm_agent.orchestrator.config import Settings


async def no_sleep(_seconds: float) -> None:
    return None


class CallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_callback_retries_transient_errors_then_succeeds(self):
        attempts = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            self.assertEqual(request.headers["Authorization"], "Bearer secret")
            return httpx.Response(503 if attempts < 3 else 200)

        settings = Settings(
            callback_url="https://backend.example/internal/ml/completed",
            callback_token="secret",
            callback_max_attempts=4,
            callback_retry_base_s=0,
            callback_total_timeout_s=5,
        )
        delivered = await notify_backend(
            "request-1", {"execution_code": "PASSED", "output_path": "/result.wav"}, settings,
            transport=httpx.MockTransport(handler), sleep=no_sleep,
        )
        self.assertTrue(delivered)
        self.assertEqual(attempts, 3)

    async def test_callback_does_not_retry_authentication_error(self):
        attempts = 0

        async def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            return httpx.Response(401)

        settings = Settings(
            callback_url="https://backend.example/internal/ml/completed",
            callback_token="wrong",
            callback_max_attempts=4,
            callback_retry_base_s=0,
        )
        delivered = await notify_backend(
            "request-2", {"execution_code": "FAILED"}, settings,
            transport=httpx.MockTransport(handler), sleep=no_sleep,
        )
        self.assertFalse(delivered)
        self.assertEqual(attempts, 1)


if __name__ == "__main__":
    unittest.main()
