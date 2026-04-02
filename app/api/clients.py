from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_admin
from app.core.cache import delete_cache, get_cache, set_cache
from app.core.limiter import limiter
from app.core.logger import logger
from app.models import Client, User

router = APIRouter()


class ClientCreate(BaseModel):
    name: str
    email: str
    client_type: str = "individual"


class ClientResponse(BaseModel):
    id: str
    name: str
    email: str
    client_type: str

    model_config = {"from_attributes": True}


@router.post("/", response_model=ClientResponse, status_code=201)
@limiter.limit("20/minute")
async def create_client(
    request: Request,
    payload: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    logger.info(f"Creating client: name={payload.name} by user={current_user.username}")
    client = Client(
        name=payload.name,
        email=payload.email,
        client_type=payload.client_type,
    )
    db.add(client)
    await db.flush()

    # Инвалидируем кеш первой страницы — данные изменились.
    await delete_cache("clients:list:page=1:limit=20")
    logger.info(f"Cache invalidated after creating client: {client.id}")

    return ClientResponse.model_validate(client)


@router.get("/", response_model=list[ClientResponse])
@limiter.limit("30/minute")
async def list_clients(
    request: Request,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if limit > 100:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 100")

    cache_key = f"clients:list:page={page}:limit={limit}"
    # Уникальный ключ для каждой комбинации page и limit.

    cached = await get_cache(cache_key)
    if cached:
        logger.info(f"Cache hit: {cache_key}")
        return cached
    # Если данные есть в Redis — возвращаем сразу без запроса в БД.

    logger.info(f"Cache miss: {cache_key}")
    offset = (page - 1) * limit
    result = await db.execute(
        select(Client)
        .order_by(Client.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    clients = result.scalars().all()
    data = [ClientResponse.model_validate(c).model_dump() for c in clients]

    await set_cache(cache_key, data, ttl=60)
    # Сохраняем в Redis на 60 секунд.

    return data


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Client).where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return ClientResponse.model_validate(client)


@router.delete("/{client_id}", status_code=204)
async def delete_client(
    client_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(Client).where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        logger.warning(f"Client not found: id={client_id}")
        raise HTTPException(status_code=404, detail="Client not found")

    await db.delete(client)

    # Инвалидируем кеш после удаления.
    await delete_cache("clients:list:page=1:limit=20")
    logger.info(f"Deleting client: id={client_id} by user={current_user.username}")