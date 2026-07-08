from fastapi import FastAPI, status
from pydantic import BaseModel
from app.api import auth, health, users

app = FastAPI(title="LLM Chat Backend")


app.include_router(auth.router)
app.include_router(health.router)
# app.include_router(chat.router)
app.include_router(users.router)

# # ----------------------------
# # Mock Data
# # ----------------------------

# conversations = [
#     {"id": 1, "title": "JWT Authentication"},
#     {"id": 2, "title": "FastAPI Crash Course"},
#     {"id": 3, "title": "LangChain Basics"},
# ]


# # ----------------------------
# # Schemas
# # ----------------------------

# class ChatRequest(BaseModel):
#     message: str


# class User(BaseModel):
#     name: str
#     age: int
#     email: str


# class UserResponse(BaseModel):
#     id: int
#     name: str


# # ----------------------------
# # Routes
# # ----------------------------

# @app.get("/")
# def home():
#     return {
#         "service": "LLM Chat service",
#         "status": "running"
#     }


# @app.get("/health")
# def health_check():
#     return {
#         "status": "ok"
#     }


# @app.get("/conversations")
# def get_conversations():
#     return conversations


# @app.get("/conversations/{conversation_id}")
# def get_conversation(conversation_id: int):
#     return {
#         "conversation_id": conversation_id
#     }


# @app.get("/messages")
# def get_messages(
#     conversation_id: int,
#     page: int = 1,
#     limit: int = 20
# ):
#     return {
#         "conversation_id": conversation_id,
#         "page": page,
#         "limit": limit
#     }


# @app.post("/users/register",
#           response_model=UserResponse,
#           status_code=status.HTTP_201_CREATED)
# def register_user(user: User):
#     return {
#         "id": 1,
#         "name": user.name,
#         "password": "super-secret-password"
#     }


# @app.post("/chat")
# def chat(request: ChatRequest):
#     return {
#         "user_message": request.message,
#         "assistant_response": "LLM response will come here."
#     }