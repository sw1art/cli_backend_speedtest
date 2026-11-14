import pytest

from app.presentation.dependencies import get_message_publisher, get_task_repository
from tests.fakes import FakePublisher, FakeTaskRepository


@pytest.fixture
def repository() -> FakeTaskRepository:
    return FakeTaskRepository()


@pytest.fixture
def publisher() -> FakePublisher:
    return FakePublisher()


@pytest.fixture
def app_with_overrides(repository, publisher):
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_task_repository] = lambda: repository
    app.dependency_overrides[get_message_publisher] = lambda: publisher
    return app
