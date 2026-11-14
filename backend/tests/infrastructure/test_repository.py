import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.entities.download_task import DownloadTask
from app.domain.value_objects.benchmark import RequestResult
from app.domain.value_objects.task_status import TaskStatus
from app.infrastructure.database.base import Base
from app.infrastructure.repositories.sqlalchemy_task_repository import SQLAlchemyTaskRepository


@pytest.fixture
async def repository():
    # Use a project-local SQLite file so the test does not depend on the
    # system temp directory (which may be unwritable in some environments).
    db_file = f".test_repository_{uuid.uuid4().hex}.db"
    url = f"sqlite+aiosqlite:///{db_file}"
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield SQLAlchemyTaskRepository(factory)
    await engine.dispose()
    try:
        os.remove(db_file)
    except OSError:
        pass


async def test_add_and_get_roundtrip(repository):
    task = DownloadTask.create(url="https://example.com/x", total_requests=2)
    task.start()
    task.results = [RequestResult(1, 1.0, 1000, 200, True)]
    task.complete()

    await repository.add(task)
    fetched = await repository.get(task.id)

    assert fetched is not None
    assert fetched.status is TaskStatus.COMPLETED
    assert fetched.url == "https://example.com/x"
    assert len(fetched.results) == 1
    assert fetched.results[0].bytes_downloaded == 1000


async def test_update_replaces_results(repository):
    task = DownloadTask.create(url="https://example.com/x", total_requests=1)
    await repository.add(task)

    task.start()
    task.results = [RequestResult(1, 1.5, 2500, 200, True)]
    task.complete()
    await repository.update(task)

    fetched = await repository.get(task.id)
    assert fetched.status is TaskStatus.COMPLETED
    assert len(fetched.results) == 1
    assert fetched.results[0].bytes_downloaded == 2500


async def test_get_missing_task_returns_none(repository):
    import uuid

    assert await repository.get(uuid.uuid4()) is None


async def test_list_and_count(repository):
    for i in range(3):
        await repository.add(DownloadTask.create(url=f"https://example.com/{i}"))
    assert await repository.count() == 3
    tasks = await repository.list(limit=2, offset=0)
    assert len(tasks) == 2
