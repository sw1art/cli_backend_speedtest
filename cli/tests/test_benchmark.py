import httpx
import pytest

from download_benchmark.benchmark import (
    BenchmarkSummary,
    DownloadBenchmarker,
    RequestResult,
    validate_url,
)
from download_benchmark.errors import InvalidURLError


def make_result(index, elapsed, size, status=200, success=True, error=None):
    return RequestResult(index, elapsed, size, status, success, error)


# --- URL validation ---------------------------------------------------------


def test_validate_url_accepts_http_and_https():
    assert validate_url("http://example.com/a.png") == "http://example.com/a.png"
    assert validate_url("https://example.com/a.png").startswith("https://")


@pytest.mark.parametrize(
    "url",
    ["", "   ", "ftp://example.com/a", "not a url", "https://"],
)
def test_validate_url_rejects_invalid(url):
    with pytest.raises(InvalidURLError):
        validate_url(url)


# --- Summary statistics -----------------------------------------------------


def test_summary_averages_and_speed():
    results = [
        make_result(1, 1.0, 1_000_000),
        make_result(2, 2.0, 2_000_000),
    ]
    summary = BenchmarkSummary(url="https://example.com/x", requested=2, results=results)
    assert summary.successful == 2
    assert summary.failed == 0
    assert summary.total_bytes == 3_000_000
    assert summary.average_time == pytest.approx(1.5)
    assert summary.average_speed == pytest.approx(1_000_000)


def test_summary_ignores_failed_requests():
    results = [
        make_result(1, 1.0, 1_000_000),
        make_result(2, 1.0, 0, status=None, success=False, error="timeout"),
    ]
    summary = BenchmarkSummary(url="u", requested=2, results=results)
    assert summary.successful == 1
    assert summary.failed == 1
    assert summary.total_bytes == 1_000_000
    assert summary.average_time == pytest.approx(1.0)


def test_summary_empty_has_no_averages():
    summary = BenchmarkSummary(url="u", requested=0, results=[])
    assert summary.average_time is None
    assert summary.average_speed is None


# --- Benchmarker ------------------------------------------------------------


def test_run_performs_sequential_requests():
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(200, content=b"x" * 100)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    summary = DownloadBenchmarker(client=client).run("https://example.com/file", requests=4)
    assert len(calls) == 4
    assert summary.successful == 4
    assert summary.total_bytes == 400


def test_http_error_is_recorded_as_failure():
    def handler(request):
        return httpx.Response(404, content=b"not found")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    summary = DownloadBenchmarker(client=client).run("https://example.com/x", requests=2)
    assert summary.successful == 0
    assert all(not r.success for r in summary.results)
    assert all(r.status_code == 404 for r in summary.results)
    assert summary.average_speed is None


def test_connection_error_is_recorded_as_failure():
    def handler(request):
        raise httpx.ConnectError("boom", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    summary = DownloadBenchmarker(client=client).run("https://example.com/x", requests=2)
    assert summary.successful == 0
    assert all(r.status_code is None for r in summary.results)
    assert all("boom" in r.error for r in summary.results)


def test_summary_latency_statistics():
    results = [
        make_result(1, 1.0, 100),
        make_result(2, 2.0, 100),
        make_result(3, 3.0, 100),
        make_result(4, 4.0, 100),
    ]
    summary = BenchmarkSummary(url="u", requested=4, results=results)
    assert summary.min_time == 1.0
    assert summary.max_time == 4.0
    assert summary.median_time == pytest.approx(2.5)
    assert summary.p95_time == pytest.approx(3.85)
    assert summary.stddev_time == pytest.approx(1.2909944487358056)


def test_requests_send_identity_encoding():
    captured = {}

    def handler(request):
        captured["accept_encoding"] = request.headers.get("accept-encoding")
        return httpx.Response(200, content=b"x" * 100)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    DownloadBenchmarker(client=client).run("https://example.com/file", requests=1)
    assert captured["accept_encoding"] == "identity"
