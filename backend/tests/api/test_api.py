from fastapi.testclient import TestClient

from app.domain.entities.download_task import DownloadTask
from app.domain.value_objects.benchmark import RequestResult
from tests.fakes import FakePublisher, FakeTaskRepository


def _client(repository=None, publisher=None):
    from app.main import create_app
    from app.presentation.dependencies import (
        get_message_publisher,
        get_task_repository,
        get_url_guard,
    )

    repository = repository or FakeTaskRepository()
    publisher = publisher or FakePublisher()
    app = create_app()
    app.dependency_overrides[get_task_repository] = lambda: repository
    app.dependency_overrides[get_message_publisher] = lambda: publisher
    # Skip the SSRF guard in API tests (it is covered by dedicated unit tests).
    app.dependency_overrides[get_url_guard] = lambda: None
    return TestClient(app)


def test_health():
    client = _client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_task():
    repo = FakeTaskRepository()
    pub = FakePublisher()
    client = _client(repo, pub)

    response = client.post("/api/v1/tasks", json={"url": "https://example.com/image.jpg"})
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "PENDING"
    assert data["total_requests"] == 10
    assert len(pub.published) == 1

    task_id = data["id"]
    status_resp = client.get(f"/api/v1/tasks/{task_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "PENDING"


def test_create_task_invalid_url():
    client = _client()
    response = client.post("/api/v1/tasks", json={"url": "ftp://example.com/x"})
    assert response.status_code == 422


def test_create_task_invalid_request_count():
    client = _client()
    response = client.post(
        "/api/v1/tasks", json={"url": "https://example.com/x", "total_requests": 0}
    )
    assert response.status_code == 422


def test_get_missing_task_returns_404():
    client = _client()
    response = client.get("/api/v1/tasks/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_list_tasks():
    repo = FakeTaskRepository()
    client = _client(repo)
    client.post("/api/v1/tasks", json={"url": "https://example.com/a"})
    client.post("/api/v1/tasks", json={"url": "https://example.com/b"})

    response = client.get("/api/v1/tasks")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_get_results():
    task = DownloadTask.create(url="https://example.com/x", total_requests=1)
    task.start()
    task.results = [RequestResult(1, 1.0, 1000, 200, True)]
    task.complete()
    repo = FakeTaskRepository([task])
    client = _client(repo)

    response = client.get(f"/api/v1/tasks/{task.id}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["summary"]["successful"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["bytes_downloaded"] == 1000
