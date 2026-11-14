import pytest

from app.domain.entities.download_task import DownloadTask
from app.domain.exceptions import InvalidTaskStatusTransition, InvalidURL
from app.domain.services.url_validation import validate_url
from app.domain.value_objects.benchmark import BenchmarkSummary, RequestResult
from app.domain.value_objects.task_status import TaskStatus


def test_benchmark_summary():
    results = [
        RequestResult(1, 1.0, 1_000_000, 200, True),
        RequestResult(2, 2.0, 2_000_000, 200, True),
    ]
    summary = BenchmarkSummary.from_results(results)
    assert summary.successful == 2
    assert summary.failed == 0
    assert summary.total_bytes == 3_000_000
    assert summary.average_time_seconds == pytest.approx(1.5)
    assert summary.average_speed_bytes_per_second == pytest.approx(1_000_000)


def test_benchmark_summary_excludes_failures():
    results = [
        RequestResult(1, 1.0, 1_000_000, 200, True),
        RequestResult(2, 0.5, 0, None, False, "timeout"),
    ]
    summary = BenchmarkSummary.from_results(results)
    assert summary.successful == 1
    assert summary.failed == 1
    assert summary.total_bytes == 1_000_000
    assert summary.average_time_seconds == pytest.approx(1.0)


def test_benchmark_summary_empty():
    summary = BenchmarkSummary.from_results([])
    assert summary.successful == 0
    assert summary.average_time_seconds is None
    assert summary.average_speed_bytes_per_second is None


def test_url_validation_accepts_http_and_https():
    assert validate_url("https://example.com/a.png") == "https://example.com/a.png"
    assert validate_url("http://example.com/a.png") == "http://example.com/a.png"


@pytest.mark.parametrize("url", ["", "ftp://example.com/a", "not a url", "https://"])
def test_url_validation_rejects_invalid(url):
    with pytest.raises(InvalidURL):
        validate_url(url)


def test_task_lifecycle():
    task = DownloadTask.create(url="https://example.com/x")
    assert task.status is TaskStatus.PENDING
    task.start()
    assert task.status is TaskStatus.PROCESSING
    assert task.started_at is not None
    task.results = [RequestResult(1, 1.0, 1000, 200, True)]
    task.complete()
    assert task.status is TaskStatus.COMPLETED
    assert task.finished_at is not None
    assert task.summary.total_bytes == 1000


def test_invalid_transitions():
    task = DownloadTask.create(url="https://example.com/x")
    with pytest.raises(InvalidTaskStatusTransition):
        task.complete()
    task.start()
    with pytest.raises(InvalidTaskStatusTransition):
        task.start()
    task.complete()
    with pytest.raises(InvalidTaskStatusTransition):
        task.fail("late")


def test_fail_from_pending_is_allowed():
    task = DownloadTask.create(url="https://example.com/x")
    task.fail("boom")
    assert task.status is TaskStatus.FAILED
    assert task.error_message == "boom"
