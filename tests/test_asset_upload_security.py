import asyncio
import base64

from app.dataplane.reverse.transport import asset_upload


class _FakeProxy:
    def __init__(self) -> None:
        self.feedback_calls = []

    async def acquire(self):
        return object()

    async def feedback(self, lease, feedback) -> None:
        self.feedback_calls.append((lease, feedback))


class _FakeResponse:
    status_code = 200
    headers = {"content-type": "image/png"}
    content = b"png"


def test_upload_from_input_does_not_forward_grok_auth_headers(monkeypatch):
    captured: dict[str, object] = {}
    proxy = _FakeProxy()

    async def fake_get_proxy_runtime():
        return proxy

    def fake_build_http_headers(token: str, lease=None):
        return {
            "Authorization": f"Bearer {token}",
            "Cookie": "x-userid=123; sso=secret",
        }

    def fake_build_session_kwargs(lease=None):
        return {}

    class FakeSession:
        def __init__(self, **kwargs):
            captured["session_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url: str, headers=None, timeout=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["timeout"] = timeout
            return _FakeResponse()

    async def fake_upload_file(token: str, filename: str, mime: str, b64: str):
        captured["upload_args"] = (token, filename, mime, b64)
        return "file-id", "file-uri"

    monkeypatch.setattr(asset_upload, "get_proxy_runtime", fake_get_proxy_runtime)
    monkeypatch.setattr(asset_upload, "build_http_headers", fake_build_http_headers)
    monkeypatch.setattr(asset_upload, "build_session_kwargs", fake_build_session_kwargs)
    monkeypatch.setattr(asset_upload, "ResettableSession", FakeSession)
    monkeypatch.setattr(asset_upload, "upload_file", fake_upload_file)

    result = asyncio.run(
        asset_upload.upload_from_input("secret-token", "https://example.com/demo.png")
    )

    assert result == ("file-id", "file-uri")
    assert captured["headers"] == {
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }
    assert "Authorization" not in captured["headers"]
    assert "Cookie" not in captured["headers"]
    assert captured["upload_args"] == (
        "secret-token",
        "demo.png",
        "image/png",
        base64.b64encode(b"png").decode(),
    )
