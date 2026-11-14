import httpx

from app.infrastructure.http_client.httpx_client import HttpxHttpClient


async def test_download_success():
    def handler(request):
        return httpx.Response(200, content=b"x" * 100)

    client = HttpxHttpClient(transport=httpx.MockTransport(handler))
    result = await client.download("https://example.com/x", 1)
    assert result.success is True
    assert result.bytes_downloaded == 100
    assert result.status_code == 200
    await client.aclose()


async def test_download_http_error():
    def handler(request):
        return httpx.Response(404, content=b"nf")

    client = HttpxHttpClient(transport=httpx.MockTransport(handler))
    result = await client.download("https://example.com/x", 1)
    assert result.success is False
    assert result.status_code == 404
    assert "404" in result.error_message
    await client.aclose()


async def test_download_connection_error():
    def handler(request):
        raise httpx.ConnectError("boom", request=request)

    client = HttpxHttpClient(transport=httpx.MockTransport(handler))
    result = await client.download("https://example.com/x", 1)
    assert result.success is False
    assert result.status_code is None
    assert "boom" in result.error_message
    await client.aclose()
