from fastapi import HTTPException, status
from auth.password import hash_password, verify_password
from auth.jwt_handler import create_access_token
from repositories.user_repository import UserRepository
from models.user import User
from schemas.auth import RegisterRequest, LoginRequest


class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()

    def register(self, data: RegisterRequest) -> dict:
        if self.user_repo.email_exists(data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists",
            )

        user = User(
            name=data.name.strip(),
            email=data.email.lower(),
            password=hash_password(data.password),
        )
        created = self.user_repo.create(user)
        token = create_access_token({"sub": str(created._id)})

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": created.to_response(),
        }

    def login(self, data: LoginRequest) -> dict:
        user = self.user_repo.find_by_email(data.email)
        if not user or not verify_password(data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        token = create_access_token({"sub": str(user._id)})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user.to_response(),
        }

    def get_me(self, user: User) -> dict:
        return user.to_response()
