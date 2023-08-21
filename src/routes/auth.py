from typing import List

from fastapi import APIRouter, HTTPException, Depends, status, Security, Request, BackgroundTasks, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm, HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
import cloudinary
import cloudinary.uploader
from src.conf.config import config
from src.database.db import get_db
from src.database.models import User
from src.schemas import UserSchema, UserResponseSchema, TokenModel, ResetPasswordRequest
from src.repository import users as repository_users
from src.services.auth import auth_service
from src.services.email import send_email, send_reset_password_email


router = APIRouter(prefix='/auth', tags=["auth"])
security = HTTPBearer()


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(body: UserSchema, background_tasks: BackgroundTasks, request: Request,
                 db: AsyncSession = Depends(get_db)):
    exist_user = await repository_users.get_user_by_email(body.email, db)
    if exist_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists")
    body.password = auth_service.get_password_hash(body.password)
    new_user = await repository_users.create_user(body, db)
    background_tasks.add_task(send_email, new_user.email, new_user.username, str(request.base_url))
    return {"detail": "User successfully created"}


@router.post("/login", response_model=TokenModel)
async def login(body: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await repository_users.get_user_by_email(body.username, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email")
    if not user.confirmed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not confirmed")
    if not auth_service.verify_password(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    # Generate JWT
    access_token = await auth_service.create_access_token(data={"sub": user.email})
    refresh_token = await auth_service.create_refresh_token(data={"sub": user.email})
    await repository_users.update_token(user, refresh_token, db)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.get('/refresh_token', response_model=TokenModel)
async def refresh_token(credentials: HTTPAuthorizationCredentials = Security(security),
                        db: AsyncSession = Depends(get_db)):
    token = credentials.credentials
    email = await auth_service.decode_refresh_token(token)
    user = await repository_users.get_user_by_email(email, db)
    if user.refresh_token != token:
        await repository_users.update_token(user, None, db)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token = await auth_service.create_access_token(data={"sub": email})
    refresh_token = await auth_service.create_refresh_token(data={"sub": email})
    await repository_users.update_token(user, refresh_token, db)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.get('/{username}')
async def refresh_token(username: str, db: AsyncSession = Depends(get_db)):
    print("----------------------")
    print(f"{username} open email")
    print("----------------------")
    return RedirectResponse("http://localhost:8000/static/check.png")

@router.get('/confirmed_email/{token}')
async def confirmed_email(token: str, db: AsyncSession = Depends(get_db)):
    email = await auth_service.get_email_from_token(token)
    user = await repository_users.get_user_by_email(email, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error")
    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    await repository_users.confirmed_email(email, db)
    return {"message": "Email confirmed"}


@router.post('/request_reset_password')
async def request_reset_password(email: str, background_tasks: BackgroundTasks, request: Request,
                                 db: AsyncSession = Depends(get_db)):
    exist_user = await repository_users.get_user_by_email(email, db)
    if exist_user:
        token = auth_service.create_reset_password_token(email)
        background_tasks.add_task(send_reset_password_email, exist_user.email, exist_user.username, request.base_url, token)
        return {"message": "Password reset email sent"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email"
        )


@router.post('/reset_password')
async def reset_password(reset_data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):

    email = reset_data.email
    token = reset_data.token
    new_password = reset_data.new_password

    payload = auth_service.verify_reset_password_token(token)
    if payload is not None:
        user = repository_users.get_user_by_email(email, db)
        if user:
            hashed_password = auth_service.get_password_hash(new_password)
            await repository_users.update_user_password(email, hashed_password, db)
            return {"message": "Password reset successful"}
        else:
            raise HTTPException(
                status_code=404, detail="User not found"
            )
    else:
        raise HTTPException(
            status_code=400, detail="Invalid token"
        )


@router.patch("/avatar", response_model=UserResponseSchema)
async def update_avatar_user(file: UploadFile = File(), current_user: User = Depends(auth_service.get_current_user),
                             db: AsyncSession = Depends(get_db)):

    cloudinary.config(
        cloud_name=config.cloudinary_name,
        api_key=config.cloudinary_api_key,
        api_secret=config.cloudinary_api_secret,
        secure=True
    )

    r = cloudinary.uploader.upload(file.file, public_id=f'ContactsApp/{current_user.username}', overwrite=True)
    src_url = cloudinary.CloudinaryImage(f'ContactsApp/{current_user.username}')\
                        .build_url(width=250, height=250, crop='fill', version=r.get('version'))
    user = await repository_users.update_avatar(current_user.email, src_url, db)
    return user