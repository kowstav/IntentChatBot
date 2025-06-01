# backend/app/api/v1/__init__.py
from fastapi import APIRouter
from .chatbot import router as chatbot_router # Assuming your chatbot.py has a 'router = APIRouter()'

api_router_v1 = APIRouter()

# Include routers from this version
api_router_v1.include_router(chatbot_router, prefix="/chat", tags=["Chatbot"])
# Add other routers for v1 if you have them, e.g.:
# from .users import router as users_router
# api_router_v1.include_router(users_router, prefix="/users", tags=["Users"])