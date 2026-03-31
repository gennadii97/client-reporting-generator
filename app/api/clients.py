from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
async def create_client(
    payload: ClientCreate,
    db: AsyncSession = Depends(get_db),
):
    client = Client(
        name=payload.name,
        email=payload.email,
        client_type=payload.client_type,
    )
    db.add(client)
    await db.flush()

    return ClientResponse.model_validate(client)


@router.get("/", response_model=list[ClientResponse])
async def list_clients(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Client))
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
        raise HTTPException(status_code=404, detail="Client not found")

    await db.delete(client)