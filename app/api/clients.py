from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logger import logger
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.limiter import limiter 

from app.api.deps import get_db
from app.models import Client

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
):
    logger.info(f"Creating client: name={payload.name} type={payload.client_type}")
    client = Client(
        name=payload.name,
        email=payload.email,
        client_type=payload.client_type,
    )
    db.add(client)
    await db.flush()
    logger.info(f"Client created: id={client.id}")
    return ClientResponse.model_validate(client)


@router.get("/", response_model=list[ClientResponse])
@limiter.limit("30/minute")
async def list_clients(
    request: Request,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    if limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit cannot exceed 100"
        )

    offset = (page - 1) * limit

    result = await db.execute(
        select(Client)
        .order_by(Client.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    clients = result.scalars().all()
    return [ClientResponse.model_validate(c) for c in clients]


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: str,
    db: AsyncSession = Depends(get_db),
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
):
    result = await db.execute(
        select(Client).where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()

    if not client:
        logger.warning(f"Client not found: id={client_id}")
        raise HTTPException(status_code=404, detail="Client not found")
    
    logger.info(f"Deleting client: id={client_id} name={client.name}")
    await db.delete(client)