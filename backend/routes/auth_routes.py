from fastapi import APIRouter, Depends, Response
from schemas.auth import RegisterRequest, LoginRequest, AuthResponse, UserResponse
from services.auth_service import AuthService
from auth.dependencies import get_current_user
from models.user import User
from utils.config import get_settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_auth_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/api",
    )


@router.post("/register", response_model=AuthResponse)
async def register(data: RegisterRequest, response: Response):
    service = AuthService()
    result = service.register(data)
    _set_auth_cookie(response, result["access_token"])
    return {"user": result["user"]}


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, response: Response):
    service = AuthService()
    result = service.login(data)
    _set_auth_cookie(response, result["access_token"])
    return {"user": result["user"]}


@router.post("/logout")
async def logout(response: Response):
    settings = get_settings()
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/api",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    service = AuthService()
    return service.get_me(current_user)
