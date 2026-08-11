from fastapi import APIRouter, Depends
from schemas.auth import RegisterRequest, LoginRequest, AuthResponse, UserResponse
from services.auth_service import AuthService
from auth.dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse)
async def register(data: RegisterRequest):
    service = AuthService()
    return service.register(data)


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest):
    service = AuthService()
    return service.login(data)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    service = AuthService()
    return service.get_me(current_user)
