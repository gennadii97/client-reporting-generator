from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.models import User

router = APIRouter()


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "analyst"


class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    # Проверяем что username не занят.
    result = await db.execute(
        select(User).where(User.username == payload.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    user = User(
        username=payload.username,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.flush()
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    # Находим пользователя по username.
    result = await db.execute(
        select(User).where(User.username == payload.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Важно: одна и та же ошибка для несуществующего пользователя
    # и неверного пароля. Не раскрываем какой именно случай.

    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="User is deactivated"
        )

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    # sub — стандартное поле JWT (subject), обычно username или user_id.
    # role — добавляем в токен чтобы не лезть в БД при каждом запросе.

    return TokenResponse(access_token=access_token)
