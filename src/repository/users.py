import logging
import secrets
from libgravatar import Gravatar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_mail import MessageSchema, MessageType, FastMail

from src.database.models import User
from src.schemas import UserSchema
from src.services.email import conf


async def get_user_by_email(email: str, db: AsyncSession) -> User:
    sq = select(User).filter_by(email=email)
    result = await db.execute(sq)
    user = result.scalar_one_or_none()
    logging.info(user)
    return user


async def create_user(body: UserSchema, db: AsyncSession) -> User:
    avatar = None
    try:
        g = Gravatar(body.email)
        avatar = g.get_image()
    except Exception as e:
        logging.error(e)
    new_user = User(**body.model_dump(), avatar=avatar)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def update_token(user: User, token: str | None, db: AsyncSession) -> None:
    user.refresh_token = token
    await db.commit()

async def confirmed_email(email: str, db: AsyncSession) -> None:
    user = await get_user_by_email(email, db)
    user.confirmed = True
    await db.commit()

async def generate_reset_token() -> str:
    # Генеруємо випадковий токен з використанням модуля secrets
    reset_token = secrets.token_urlsafe(32)  # Генеруємо випадковий рядок довжиною 32 символи
    return reset_token

async def get_user_by_reset_token(reset_token: str, db: AsyncSession) -> User:
    sq = select(User).filter_by(reset_token=reset_token)
    result = await db.execute(sq)
    user = result.scalar_one_or_none()
    return user

async def update_user_password(email, hashed_password, db: AsyncSession) -> None:
    user = await get_user_by_email(email, db)
    user.password = hashed_password
    db.commit()

async def update_avatar(user: User, avatar_url: str, db: AsyncSession) -> None:
    user.avatar = avatar_url
    await db.commit()
