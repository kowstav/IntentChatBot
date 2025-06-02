from fastapi import APIRouter
from .chatbot import router as chatbot_router

api_router_v1 = APIRouter()

# Include routers from this version
api_router_v1.include_router(chatbot_router, prefix="/chat", tags=["Chatbot"])