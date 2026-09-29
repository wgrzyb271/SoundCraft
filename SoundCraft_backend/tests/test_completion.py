from __future__ import annotations

import asyncio
import io
import os
import unittest
import wave
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from SoundCraft_backend.app.completion import CompletionRegistry
from SoundCraft_backend.app.config import settings
from SoundCraft_backend.app.main import app
from SoundCraft_backend.app.callback_gateway import app as gateway_app


class CompletionRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def test_notification_wakes_waiter(self):
        registry = CompletionRegistry()
        request_id = str(uuid4())
        waiter = asyncio.create_task(registry.wait(request_id, 1))
        await asyncio.sleep(0)
        await registry.mark_completed(request_id, {"status": "SUCCESS"})
        self.assertEqual(await waiter, {"status": "SUCCESS"})

    async def test_notification_is_retained_for_late_websocket(self):
        registry = CompletionRegistry()
        request_id = str(uuid4())
        await registry.mark_completed(request_id, {"status": "FAILED"})
        self.assertEqual(await registry.wait(request_id, 0.1), {"status": "FAILED"})


class CompletionEndpointTests(unittest.TestCase):
    def test_callback_requires_token(self):
        request_id = str(uuid4())
        with patch.object(settings, "callback_token", "secret"), TestClient(app) as client:
            response = client.post(
                "/internal/ml/completed",
                json={"request_id": request_id, "execution_code": "PASSED", "audio_ready": True},
                headers={"Authorization": "Bearer wrong"},
            )
        self.assertEqual(response.status_code, 401)

    def test_callback_notifies_websocket(self):
        request_id = str(uuid4())
        with patch.object(settings, "callback_token", "secret"), TestClient(app) as client:
            with client.websocket_connect(f"/ws/result/{request_id}") as websocket:
                response = client.post(
                    "/internal/ml/completed",
                    json={"request_id": request_id, "execution_code": "PASSED", "audio_ready": True},
                    headers={"Authorization": "Bearer secret"},
                )
                message = websocket.receive_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(message["status"], "completed")
        self.assertEqual(message["request_id"], request_id)
        self.assertTrue(message["audio_ready"])


class CallbackGatewayTests(unittest.TestCase):
    def test_gateway_exposes_health_only_and_forwards_callback(self):
        class FakeResponse:
            status_code = 200
            text = ""

            @staticmethod
            def json():
                return {"status": "accepted", "request_id": "forwarded"}

        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def post(self, *_args, **_kwargs):
                return FakeResponse()

        request_id = str(uuid4())
        with patch(
            "SoundCraft_backend.app.callback_gateway.httpx.AsyncClient",
            return_value=FakeClient(),
        ), TestClient(gateway_app) as client:
            self.assertEqual(client.get("/health").status_code, 200)
            self.assertEqual(client.get("/upload").status_code, 404)
            response = client.post(
                "/internal/ml/completed",
                json={"request_id": request_id, "execution_code": "PASSED"},
                headers={"Authorization": "Bearer secret"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "accepted")


class DemoWebSocketTests(unittest.TestCase):
    @staticmethod
    def _wav() -> bytes:
        output = io.BytesIO()
        with wave.open(output, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(8000)
            wav.writeframes(b"\x00\x00" * 800)
        return output.getvalue()

    def test_demo_completes_without_result_polling(self):
        with patch.dict(os.environ, {"SOUNDCRAFT_DEMO": "1"}), TestClient(app) as client:
            upload = client.post(
                "/upload",
                data={"prompt": "wyciągnij wokal"},
                files={"audio": ("test.wav", self._wav(), "audio/wav")},
            )
            self.assertEqual(upload.status_code, 200)
            request_id = upload.json()["request_id"]
            with client.websocket_connect(f"/ws/result/{request_id}") as websocket:
                notice = websocket.receive_json()
            self.assertEqual(notice["status"], "completed")
            result = client.get(f"/result/{request_id}/agent_response")
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["status"], "completed")
            client.delete(f"/result/{request_id}")


if __name__ == "__main__":
    unittest.main()
