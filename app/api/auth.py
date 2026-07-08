from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# Request Models

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# Response Models

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class MessageResponse(BaseModel):
    message: str


# Routes

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register(user: RegisterRequest):
    return {
        "id": 1,
        "name": user.name,
        "email": user.email,
        "role": "user"
    }


@router.post(
    "/login",
    response_model=TokenResponse
)
def login(user: LoginRequest):
    return {
        "access_token": "dummy-access-token",
        "refresh_token": "dummy-refresh-token",
        "token_type": "Bearer"
    }


@router.post(
    "/refresh",
    response_model=TokenResponse
)
def refresh():
    return {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "token_type": "Bearer"
    }


@router.post(
    "/forgot-password",
    response_model=MessageResponse
)
def forgot_password(user: ForgotPasswordRequest):
    return {
        "message": "If an account with that email exists, a password reset link has been sent."
    }


@router.post(
    "/reset-password",
    response_model=MessageResponse
)
def reset_password(user: ResetPasswordRequest):
    return {
        "message": "Password reset successfully"
    }


@router.patch(
    "/change-password",
    response_model=MessageResponse
)
def change_password(user: ChangePasswordRequest):
    return {
        "message": "Password changed successfully"
    }

@router.get(
    "/me",
    response_model=UserResponse
)
def get_current_user(current_user=Depends(get_current_user)):
    return current_user

@router.post(
    "/logout",
    response_model=MessageResponse
)
def logout():
    return {
        "message": "Logged out successfully"
    }