import uuid

import pytest

from app.application.dto.task_dto import CreateTaskDTO
from app.application.exceptions import MessagePublishError, TaskNotFoundError
from app.application.use_cases.create_task import CreateDownloadTask
from app.application.use_cases.execute_benchmark import ExecuteDownloadBenchmark
from app.application.use_cases.get_history import GetDownloadHistory
from app.application.use_cases.get_task import GetDownloadTask
from app.domain.entities.download_task import DownloadTask
from app.domain.exceptions import UnsafeURL
from app.domain.value_objects.benchmark import RequestResult
from app.domain.value_objects.task_status import TaskStatus
from tests.fakes import FakeHttpClient, FakePublisher, FakeTaskRepository


async def test_create_task_persists_and_publishes():
    repo = FakeTaskRepository()
    pub = FakePublisher()
    dto = await CreateDownloadTask(repo, pub).execute(
        CreateTaskDTO(url="https://example.com/x", total_requests=10)
    )
    assert dto.status == "PENDING"
    assert await repo.count() == 1
    assert pub.published == [dto.id]


async def test_create_task_publish_failure_marks_failed():
    repo = FakeTaskRepository()
    pub = FakePublisher()
    pub.fail = True
    with pytest.raises(MessagePublishError):
        await CreateDownloadTask(repo, pub).execute(CreateTaskDTO(url="https://example.com/x"))
    tasks = await repo.list()
    assert tasks[0].status is TaskStatus.FAILED


async def test_get_task_not_found():
    with pytest.raises(TaskNotFoundError):
        await GetDownloadTask(FakeTaskRepository()).execute(uuid.uuid4())


async def test_execute_benchmark_completes():
    repo = FakeTaskRepository()
    task = DownloadTask.create(url="https://example.com/x", total_requests=3)
    await repo.add(task)
    http = FakeHttpClient(
        results=[
            RequestResult(1, 1.0, 1000, 200, True),
            RequestResult(2, 1.0, 1000, 200, True),
            RequestResult(3, 1.0, 1000, 200, True),
        ]
    )
    dto = await ExecuteDownloadBenchmark(repo, http).execute(task.id)
    assert dto.status == "COMPLETED"
    assert dto.summary.successful == 3
    assert len(http.calls) == 3


async def test_execute_benchmark_all_failed_marks_failed():
    repo = FakeTaskRepository()
    task = DownloadTask.create(url="https://example.com/x", total_requests=2)
    await repo.add(task)
    http = FakeHttpClient(
        results=[
            RequestResult(1, 0.1, 0, None, False, "timeout"),
            RequestResult(2, 0.1, 0, None, False, "timeout"),
        ]
    )
    dto = await ExecuteDownloadBenchmark(repo, http).execute(task.id)
    assert dto.status == "FAILED"
    assert "All requests failed" in dto.error_message


async def test_execute_benchmark_resumes_processing_task():
    repo = FakeTaskRepository()
    task = DownloadTask.create(url="https://example.com/x", total_requests=1)
    await repo.add(task)
    task.start()  # simulate a previous attempt that already started
    http = FakeHttpClient(results=[RequestResult(1, 1.0, 500, 200, True)])
    dto = await ExecuteDownloadBenchmark(repo, http).execute(task.id)
    assert dto.status == "COMPLETED"


async def test_get_history_paginates():
    repo = FakeTaskRepository()
    for i in range(3):
        await repo.add(DownloadTask.create(url=f"https://example.com/{i}"))
    dto = await GetDownloadHistory(repo).execute(limit=2, offset=0)
    assert dto.total == 3
    assert len(dto.items) == 2


async def test_create_task_url_guard_blocks_unsafe_url():
    repo = FakeTaskRepository()
    pub = FakePublisher()

    async def guard(url):
        raise UnsafeURL("blocked")

    with pytest.raises(UnsafeURL):
        await CreateDownloadTask(repo, pub, url_guard=guard).execute(
            CreateTaskDTO(url="https://example.com/x")
        )
    assert await repo.count() == 0


async def test_execute_benchmark_url_guard_called():
    repo = FakeTaskRepository()
    task = DownloadTask.create(url="https://example.com/x", total_requests=1)
    await repo.add(task)
    http = FakeHttpClient(results=[RequestResult(1, 1.0, 500, 200, True)])

    calls = []

    async def guard(url):
        calls.append(url)

    dto = await ExecuteDownloadBenchmark(repo, http, url_guard=guard).execute(task.id)
    assert dto.status == "COMPLETED"
    assert calls == ["https://example.com/x"]
