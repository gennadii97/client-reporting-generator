import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.deps import get_current_user, get_db
from app.core.database import Base
from app.main import app
from app.models import User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

AsyncSessionTest = async_sessionmaker(
    engine_test,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    async with AsyncSessionTest() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def make_mock_user(role: str = "admin") -> User:
    user = User()
    user.id = "test-user-id"
    user.username = "testuser"
    user.role = role
    user.is_active = True
    return user


async def override_get_current_user():
    return make_mock_user(role="admin")


async def override_get_current_user_analyst():
    return make_mock_user(role="analyst")


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    # Мокируем Redis кеш — в тестах Redis недоступен.
    with patch("app.api.clients.get_cache", new_callable=AsyncMock, return_value=None), \
         patch("app.api.clients.set_cache", new_callable=AsyncMock), \
         patch("app.api.clients.delete_cache", new_callable=AsyncMock):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as ac:
            yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def analyst_client():
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user_analyst
    with patch("app.api.clients.get_cache", new_callable=AsyncMock, return_value=None), \
         patch("app.api.clients.set_cache", new_callable=AsyncMock), \
         patch("app.api.clients.delete_cache", new_callable=AsyncMock):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as ac:
            yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_client(client):
    response = await client.post(
        "/api/v1/clients/",
        json={
            "name": "Test Client",
            "email": "test@example.com",
            "client_type": "corporate",
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Client"
    assert data["client_type"] == "corporate"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_client_not_found(client):
    response = await client.get(
        "/api/v1/clients/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Client not found"


@pytest.mark.asyncio
async def test_list_clients_empty(client):
    response = await client.get("/api/v1/clients/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_and_get_client(client):
    create_response = await client.post(
        "/api/v1/clients/",
        json={"name": "Газпром", "email": "gazprom@example.com", "client_type": "corporate"}
    )
    assert create_response.status_code == 201
    client_id = create_response.json()["id"]

    get_response = await client.get(f"/api/v1/clients/{client_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Газпром"


@pytest.mark.asyncio
async def test_analyst_cannot_delete_client(analyst_client):
    response = await analyst_client.delete(
        "/api/v1/clients/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_report(client):
    create_response = await client.post(
        "/api/v1/clients/",
        json={"name": "BNP", "email": "bnp@example.com", "client_type": "corporate"}
    )
    assert create_response.status_code == 201
    client_id = create_response.json()["id"]

    mock_task = MagicMock()
    mock_task.id = "test-task-id-123"

    with patch("app.api.reports.generate_report_task.delay", return_value=mock_task):
        report_response = await client.post(
            "/api/v1/reports/generate",
            json={
                "client_id": client_id,
                "report_type": "monthly",
                "period_start": "2024-01-01",
                "period_end": "2024-01-31"
            }
        )
    assert report_response.status_code == 202
    report_id = report_response.json()["report_id"]

    delete_response = await client.delete(f"/api/v1/reports/{report_id}")
    assert delete_response.status_code == 204

    status_response = await client.get(f"/api/v1/reports/{report_id}/status")
    assert status_response.status_code == 404
