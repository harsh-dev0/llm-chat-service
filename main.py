#server
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi import status

app=FastAPI()

items = [
    {"id": 1, "name": "Item One"},
    {"id": 2, "name": "Item Two"},
    {"id": 3, "name": "Item Three"},
]
class UserResponse(BaseModel):
    id: int
    name: str

class User(BaseModel):
    name: str
    age: int
    email: str

@app.get("/")
def home():
    return {"Welcome to LLM Chat Service"}
@app.get("/health")
def health_check():
    return {"status": "ok"}
@app.get("/items")
def get_items():
    return items
@app.get("/items/:id")
def get_items(id:int):
    return items[id]
@app.get("/search")
def search(
    q: str | None = None,
    page: int = 1,
    limit: int = 10,
    active: bool = True
):
    return {
        "q": q,
        "page": page,
        "limit": limit,
        "active": active
    }

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: User):
    return {
        "id": 1,
        "name": user.name,
        "password": "secret123"
    }


