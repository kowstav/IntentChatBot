# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import your API router (assuming it's defined in chatbot.py and exposed via api.v1.__init__)
from .api.v1 import api_router_v1 # Adjusted import path
from .config import settings # Your application settings
# from .db.session import engine # If you need direct access to engine for some reason
# from .db import models # If you are using SQLAlchemy Base for create_all (usually for dev/testing)

# This line is for development/testing if you want SQLAlchemy to create tables
# based on your models. For production, Alembic migrations are preferred.
# models.Base.metadata.create_all(bind=engine) # Be cautious with this in prod

app = FastAPI(
    title="IntentChatBot API",
    version="1.0.0",
    description="API for the IntentChatBot, handling chat, NLP, and escalations."
    # You can add more OpenAPI metadata here
    # docs_url="/api/docs", openapi_url="/api/openapi.json"
)

# CORS (Cross-Origin Resource Sharing)
# Configure this according to your frontend's URL and needs.
# For development, allowing all origins might be okay, but be restrictive in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:3000"], # Add your frontend URL
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)

# Include your versioned API router
# The prefix here means all routes in api_router_v1 will start with /api/v1
app.include_router(api_router_v1, prefix="/api/v1")


@app.get("/health", tags=["Health Check"])
async def health_check():
    # You can expand this to check DB connection, Redis, NLP model status etc.
    return {"status": "ok", "message": "API is healthy"}

# If you have other routers or specific event handlers (startup/shutdown), add them here.
# For example, if you have a more complex NLP model loading or DB connection pool setup:
# from .core.nlp import classifier # Assuming classifier is your loaded NLP model instance
# from .db.session import redis_client # If you initialize redis client globally

@app.on_event("startup")
async def startup_event():
    print("Application startup complete.")
    # Initialize NLP model if not done elsewhere, connect to Redis, etc.
    # (This is often handled within the modules themselves or via dependency injection)
    # Example:
    # if not classifier.model_loaded: # Hypothetical check
    #     classifier.load_model()
    # if not redis_client.is_connected():
    #     await redis_client.connect()
    pass

@app.on_event("shutdown")
async def shutdown_event():
    print("Application shutdown.")
    # Clean up resources, e.g., close Redis connection pool
    # if redis_client and redis_client.is_connected():
    #     await redis_client.close()
    pass

# To run this app (if this file is executed directly, though uvicorn from CLI is standard):
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")