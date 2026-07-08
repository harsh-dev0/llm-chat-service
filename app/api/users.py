from fastapi import APIRouter
from pydantic import BaseModel

router=APIRouter(prefix="/users", tags=["Users"])

class UserResponse(BaseModel):
    id: str
    name: str
    email: str

class UpdateUser(BaseModel):
    name: str
    phone: int


@router.get("/{id}", 
            response_model=UserResponse)
def get_user_details(id: str):
    return {
    "id": id,
    "name": "Harsh",
    "email": "harsh@gmail.com"
}

@router.patch("/{id}", 
              response_model=UpdateUser)
def update_user(id: str, user: UpdateUser):
    return {
        "id": id,
        "name": user.name,
        "email": "harsh@gmail.com"
    }