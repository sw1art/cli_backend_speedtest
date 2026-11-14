import json

import pytest

from download_benchmark.benchmark import RequestResult
from download_benchmark.cli import main


class FakeBenchmarker:
    def __init__(self, results):
        self.results = list(results)

    def iter_results(self, url, requests):
        yield from self.results


def test_main_success(capsys):
    fake = FakeBenchmarker(
        [
            RequestResult(1, 1.0, 1_000_000, 200, True),
            RequestResult(2, 1.0, 1_000_000, 200, True),
        ]
    )
    code = main(["https://example.com/file", "-n", "2"], benchmarker=fake)
    assert code == 0
    out = capsys.readouterr().out
    assert "Average speed" in out
    assert "2.00 MB" in out


def test_main_json(capsys):
    fake = FakeBenchmarker([RequestResult(1, 1.0, 1_000_000, 200, True)])
    code = main(["https://example.com/file", "-n", "1", "--json"], benchmarker=fake)
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["successful"] == 1
    assert data["total_bytes"] == 1_000_000


def test_main_invalid_url_returns_usage_error():
    with pytest.raises(SystemExit) as exc:
        main(["not-a-valid-url"])
    assert exc.value.code == 2


def test_main_all_failed_returns_nonzero(capsys):
    fake = FakeBenchmarker([RequestResult(1, 0.5, 0, None, False, "connection error")])
    code = main(["https://example.com/file", "-n", "1"], benchmarker=fake)
    assert code == 3
