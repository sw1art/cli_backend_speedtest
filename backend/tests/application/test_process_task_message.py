import uuid

import pytest

from app.application.use_cases.execute_benchmark import ExecuteDownloadBenchmark
from app.application.use_cases.fail_task import FailDownloadTask
from app.application.use_cases.process_task_message import (
    ProcessTaskMessage,
    parse_message_body,
)
from app.domain.entities.download_task import DownloadTask
from app.domain.value_objects.benchmark import RequestResult
from app.domain.value_objects.task_status import TaskStatus
from tests.fakes import FakeHttpClient, FakePublisher, FakeTaskRepository


def test_parse_message_body_valid():
    body = b'{"task_id": "00000000-0000-0000-0000-000000000001", "retry_count": 2}'
    task_id, retry_count = parse_message_body(body)
    assert task_id == uuid.UUID("00000000-0000-0000-0000-000000000001")
    assert retry_count == 2


def test_parse_message_body_defaults_retry_count():
    body = b'{"task_id": "00000000-0000-0000-0000-000000000001"}'
    assert parse_message_body(body)[1] == 0


@pytest.mark.parametrize("body", [b"not json", b'{"x": 1}', b'{"task_id": "nope"}'])
def test_parse_message_body_malformed(body):
    assert parse_message_body(body) is None


def _processor(repo, http, publisher, on_status, max_retries=2):
    execute = ExecuteDownloadBenchmark(repo, http)
    fail_task = FailDownloadTask(repo)
    return ProcessTaskMessage(
        execute=execute,
        fail_task=fail_task,
        publisher=publisher,
        max_retries=max_retries,
        retry_delay_ms=100,
        on_status=on_status,
    )


async def test_process_malformed_message_does_nothing():
    repo = FakeTaskRepository()
    pub = FakePublisher()
    statuses = []
    processor = _processor(repo, FakeHttpClient(), pub, statuses.append)
    await processor.process(b"not json")
    assert statuses == []
    assert pub.published == []
    assert pub.retried == []


async def test_process_success_records_completed():
    repo = FakeTaskRepository()
    task = DownloadTask.create(url="https://example.com/x", total_requests=1)
    await repo.add(task)
    http = FakeHttpClient(results=[RequestResult(1, 1.0, 500, 200, True)])
    statuses = []
    processor = _processor(repo, http, FakePublisher(), statuses.append)
    await processor.process(f'{{"task_id": "{task.id}"}}'.encode())
    assert statuses == ["COMPLETED"]


async def test_process_all_failed_records_failed():
    repo = FakeTaskRepository()
    task = DownloadTask.create(url="https://example.com/x", total_requests=1)
    await repo.add(task)
    http = FakeHttpClient(results=[RequestResult(1, 0.1, 0, None, False, "timeout")])
    statuses = []
    processor = _processor(repo, http, FakePublisher(), statuses.append)
    await processor.process(f'{{"task_id": "{task.id}"}}'.encode())
    assert statuses == ["FAILED"]


async def test_process_retries_on_exception():
    repo = FakeTaskRepository()
    task = DownloadTask.create(url="https://example.com/x", total_requests=1)
    await repo.add(task)
    http = FakeHttpClient(exc=RuntimeError("boom"))
    pub = FakePublisher()
    statuses = []
    processor = _processor(repo, http, pub, statuses.append, max_retries=2)
    await processor.process(f'{{"task_id": "{task.id}", "retry_count": 0}}'.encode())
    assert statuses == []
    assert len(pub.retried) == 1
    assert pub.retried[0][0] == task.id
    assert pub.retried[0][1] == 1
    assert pub.retried[0][2] == 100


async def test_process_fails_after_exhausting_retries():
    repo = FakeTaskRepository()
    task = DownloadTask.create(url="https://example.com/x", total_requests=1)
    await repo.add(task)
    http = FakeHttpClient(exc=RuntimeError("boom"))
    pub = FakePublisher()
    statuses = []
    processor = _processor(repo, http, pub, statuses.append, max_retries=1)
    await processor.process(f'{{"task_id": "{task.id}", "retry_count": 1}}'.encode())
    assert statuses == ["FAILED"]
    fetched = await repo.get(task.id)
    assert fetched.status is TaskStatus.FAILED
    assert pub.retried == []


async def test_process_task_not_found_drops():
    repo = FakeTaskRepository()
    pub = FakePublisher()
    statuses = []
    processor = _processor(repo, FakeHttpClient(), pub, statuses.append)
    missing = uuid.uuid4()
    await processor.process(f'{{"task_id": "{missing}"}}'.encode())
    assert statuses == []
    assert pub.retried == []
