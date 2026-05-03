from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import create_access_token
from app.core.config import settings
from app.schemas import UserCreate, UserLogin, UserResponse, Token
from app.services import auth_service
from app.api.deps import get_current_active_user

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate
):
    existing_user = await auth_service.get_user_by_username(user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    user = await auth_service.create_user(user_in)
    return user


@router.post("/login", response_model=Token)
async def login(
    user_in: UserLogin
):
    user = await auth_service.authenticate_user(user_in.username, user_in.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.get("account_status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive or suspended"
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_active_user)
):
    return current_user
