"""Verifies the global exception handler never leaks internals to the
client — the full traceback goes to the server log only (see
backend/api/middleware.py, added as part of V1.0's security hardening).
"""
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.main import app


def test_unhandled_exception_returns_generic_500(client):
    # The shared `client` fixture re-raises server exceptions (useful for
    # catching bugs elsewhere), so this test needs its own client with that
    # off, to observe the actual HTTP response our handler produces. It
    # reuses the same dependency override `client` already installed.
    non_raising_client = TestClient(app, raise_server_exceptions=False)
    secret_detail = "some internal detail that must never reach the client"
    with patch(
        "backend.api.routers.candidates.EvidenceStore.get_candidate",
        side_effect=RuntimeError(secret_detail),
    ):
        resp = non_raising_client.get("/candidates/any-id")

    assert resp.status_code == 500
    body = resp.json()
    assert body == {"detail": "Internal server error"}
    assert secret_detail not in resp.text
