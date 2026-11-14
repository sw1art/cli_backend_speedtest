from download_benchmark.benchmark import BenchmarkSummary, RequestResult
from download_benchmark.formatter import (
    format_result,
    human_size,
    human_speed,
    render_report,
)


def test_human_size_decimal_units():
    assert human_size(0) == "0 B"
    assert human_size(999) == "999 B"
    assert human_size(1000) == "1.00 KB"
    assert human_size(2_500_000) == "2.50 MB"
    assert human_size(1_000_000_000) == "1.00 GB"


def test_human_speed():
    assert human_speed(2_000_000) == "2.00 MB/s"


def test_format_result_success():
    result = RequestResult(1, 1.24, 2_500_000, 200, True)
    assert format_result(result) == "Request 1: 1.24 sec | 2.50 MB"


def test_format_result_http_error():
    result = RequestResult(2, 0.1, 1200, 404, False, "HTTP 404")
    assert "HTTP 404" in format_result(result)


def test_format_result_connection_error():
    result = RequestResult(2, 0.1, 0, None, False, "connection timeout")
    assert "ERROR" in format_result(result)
    assert "connection timeout" in format_result(result)


def test_render_report_contains_averages():
    summary = BenchmarkSummary(
        url="https://example.com/x",
        requested=2,
        results=[
            RequestResult(1, 1.0, 1_000_000, 200, True),
            RequestResult(2, 1.0, 1_000_000, 200, True),
        ],
    )
    text = render_report(summary)
    assert "Average request time: 1.00 sec" in text
    assert "Total downloaded: 2.00 MB" in text
    assert "Average speed: 1.00 MB/s" in text
