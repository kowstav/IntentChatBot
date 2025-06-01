# main.py
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uuid
import datetime
import json
import time # For simulating delays
import random # For mocking
import asyncio # For async mock functions

# --- Hugging Face Transformers ---
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# --- Redis ---
# You'll need to install: pip install redis[hiredis]
import redis.asyncio as aioredis # For asynchronous Redis operations

# --- Configuration ---
MOCKED_ORDER_API_URL = "http://localhost:8001/orders"
MOCKED_USER_API_URL = "http://localhost:8002/users"

# --- Redis Configuration ---
# Ensure your Redis server is running and accessible.
# Update these if your Redis server is not on localhost or default port.
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_PASSWORD = None # Add your Redis password here if it's set, otherwise leave as None
REDIS_ESCALATION_QUEUE_NAME = "escalation_queue"

POSTGRES_DSN = "postgresql://user:password@host:port/database" # Placeholder for DB config

# --- NLP Model Setup ---
NLP_MODEL_NAME = "distilbert-base-uncased" # Using a base model for structure example
INTENT_MAP = {
    0: "greet", 1: "goodbye", 2: "track_order", 3: "request_return",
    4: "request_refund", 5: "product_inquiry", 6: "account_issue",
    7: "request_human_agent", 8: "other_fallback"
}
tokenizer = None
model = None
redis_client = None # Global Redis client instance

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str
    user_id: str | None = None

class ChatResponse(BaseModel):
    session_id: str
    response_message: str
    escalated: bool = False
    escalation_ticket_id: str | None = None
    debug_intent: str | None = None
    confidence: float | None = None

class FeedbackRequest(BaseModel):
    session_id: str
    chat_log_id: int | None = None
    rating: int
    comment: str | None = None

class FeedbackResponse(BaseModel):
    status: str
    feedback_id: int

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Smart Customer Support Chatbot API",
    description="API for the chatbot system with NLP and Redis-based escalation.",
    version="0.3.0" # Version bump
)

# --- Lifecycle Events for Model & Redis Loading ---
@app.on_event("startup")
async def startup_event():
    global tokenizer, model, redis_client
    # Load NLP Model
    try:
        print(f"Loading NLP model: {NLP_MODEL_NAME}")
        tokenizer = AutoTokenizer.from_pretrained(NLP_MODEL_NAME)
        # For a real intent model, specify num_labels, e.g., num_labels=len(INTENT_MAP)
        model = AutoModelForSequenceClassification.from_pretrained(NLP_MODEL_NAME)
        model.eval()
        print("NLP Model and Tokenizer loaded successfully.")
    except Exception as e:
        print(f"Error loading NLP model: {e}")
        tokenizer = None
        model = None

    # Initialize Redis Client
    try:
        print(f"Connecting to Redis server at {REDIS_HOST}:{REDIS_PORT}")
        # Ensure your Redis server is running and configured correctly.
        # If your Redis requires a password, set it in REDIS_PASSWORD config.
        redis_client = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=True)
        await redis_client.ping() # Check connection
        print("Successfully connected to Redis.")
    except Exception as e:
        print(f"Error connecting to Redis: {e}")
        print("Redis features (like escalation queue) will not be available.")
        redis_client = None # Set to None if connection fails

@app.on_event("shutdown")
async def shutdown_event():
    global redis_client
    if redis_client:
        print("Closing Redis connection.")
        await redis_client.close()


# --- In-memory storage (Replace with DB/Redis) ---
chat_sessions_db = {}
chat_logs_db = []
escalations_db = {} # This will be partially replaced by Redis for queueing
feedback_db = []
log_id_counter = 1
feedback_id_counter = 1

# --- Mocked External Systems ---
async def mock_get_order_status(order_id: str):
    await asyncio.sleep(0.2) # Reduced delay
    mock_orders = {
        "12345": {"status": "Shipped", "estimated_delivery": "2025-06-05", "items": ["Awesome Gadget Pro"]},
        "67890": {"status": "Processing", "estimated_delivery": "2025-06-08", "items": ["Super Widget"]},
    }
    return mock_orders.get(order_id)

async def mock_get_product_info(product_name: str):
    await asyncio.sleep(0.1) # Reduced delay
    product_name_lower = product_name.lower()
    mock_products = {
        "awesome gadget pro": {"price": "$99.99", "in_stock": True, "features": "Latest model, 10x faster."},
        "super widget": {"price": "$49.50", "in_stock": False, "restock_date": "2025-06-15"},
    }
    for name, data in mock_products.items():
        if product_name_lower in name:
            return data
    return None

# --- Intent Classification Module (Using Hugging Face Model) ---
def classify_intent_with_hf(message: str) -> tuple[str, float, dict]:
    entities = {}
    if not tokenizer or not model:
        print("Warning: NLP model not loaded. Using basic keyword matching.")
        message_lower = message.lower() # Simplified fallback
        intent_name = "other_fallback"
        if "order" in message_lower or "track" in message_lower: intent_name = "track_order"
        elif "return" in message_lower: intent_name = "request_return"
        elif "hello" in message_lower or "hi" in message_lower: intent_name = "greet"
        return intent_name, 0.5, entities

    try:
        inputs = tokenizer(message, return_tensors="pt", truncation=True, padding=True, max_length=512)
        with torch.no_grad():
            outputs = model(**inputs)
        probabilities = torch.softmax(outputs.logits, dim=-1)
        predicted_class_id = torch.argmax(probabilities, dim=-1).item()
        confidence = probabilities[0, predicted_class_id].item()
        intent_name = INTENT_MAP.get(predicted_class_id, "other_fallback")

        message_lower = message.lower() # For entity extraction
        if intent_name == "track_order":
            words = message.split()
            for word in words:
                if word.isdigit() and len(word) >= 5: entities["order_id"] = word; break
                if word.isalnum() and not word.isdigit() and not word.isalpha() and len(word) >=5: entities["order_id"] = word; break
        elif intent_name == "product_inquiry":
            keywords_to_remove = ["tell me about", "product info for", "is", "in stock", "how much is", "the", "a", "an"]
            temp_message = message_lower
            for kw in keywords_to_remove: temp_message = temp_message.replace(kw, "")
            entities["product_name"] = temp_message.strip().replace("?","")
        return intent_name, confidence, entities
    except Exception as e:
        print(f"Error during NLP intent classification: {e}")
        return "other_fallback", 0.0, entities


# --- Business Logic & Orchestration ---
async def handle_chat_logic(session_id: str, user_message: str, user_id: str | None) -> ChatResponse:
    global log_id_counter, redis_client
    intent, confidence, entities = classify_intent_with_hf(user_message)
    response_message = "I'm sorry, I didn't quite understand that. Could you please rephrase?"
    escalated = False
    escalation_ticket_id = None

    # Log user message (to in-memory list, replace with DB)
    chat_logs_db.append({
        "log_id": log_id_counter, "session_id": session_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sender": "user", "message_text": user_message,
        "intent_classified": intent, "confidence_score": confidence,
    })
    log_id_counter += 1

    CONFIDENCE_THRESHOLD = 0.6
    if confidence < CONFIDENCE_THRESHOLD and intent != "request_human_agent":
        print(f"Low confidence ({confidence:.2f}) for intent '{intent}'. Treating as fallback.")
        intent = "other_fallback"

    # --- Escalation Handling Function ---
    async def _trigger_escalation(reason_text: str):
        nonlocal escalated, escalation_ticket_id, response_message # Allow modification of outer scope variables
        escalated = True
        escalation_ticket_id = f"ESC-{uuid.uuid4().hex[:10].upper()}"
        current_time_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Prepare escalation data
        escalation_data = {
            "escalation_ticket_id": escalation_ticket_id,
            "session_id": session_id,
            "user_id": user_id, # Include user_id if available
            "escalation_time": current_time_iso,
            "reason": reason_text,
            "status": "pending", # Initial status
            "initial_query": user_message,
            # You might want to include recent chat history snippet here
            # "chat_history_snippet": [msg for msg in chat_logs_db if msg['session_id'] == session_id][-5:] # Last 5 messages
        }

        # Log to in-memory escalations_db (replace with PostgreSQL)
        escalations_db[escalation_ticket_id] = escalation_data
        if session_id in chat_sessions_db:
            chat_sessions_db[session_id]["status"] = "escalated"

        # Push to Redis Queue if Redis is available
        if redis_client:
            try:
                await redis_client.lpush(REDIS_ESCALATION_QUEUE_NAME, json.dumps(escalation_data))
                print(f"Successfully pushed escalation ticket {escalation_ticket_id} to Redis queue '{REDIS_ESCALATION_QUEUE_NAME}'.")
                # A separate worker process would listen to this Redis queue (e.g., using BRPOP)
                # and pick up tasks for human agents.
            except Exception as e:
                print(f"Error pushing escalation to Redis: {e}. Escalation logged locally.")
                # Fallback: Ensure escalation is still logged, even if Redis fails.
        else:
            print("Redis client not available. Escalation logged locally only.")
        
        return escalation_ticket_id # Return the ticket ID

    # --- Intent-based response generation ---
    if intent == "greet":
        response_message = random.choice(["Hello! How can I help?", "Hi there! What's up?", "Hey! How can I assist?"])
    elif intent == "goodbye":
        response_message = random.choice(["Goodbye!", "Thanks for chatting!", "Take care!"])
        if session_id in chat_sessions_db:
            chat_sessions_db[session_id]["status"] = "resolved_bot"
            chat_sessions_db[session_id]["end_time"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    elif intent == "track_order":
        order_id = entities.get("order_id")
        if order_id:
            order_data = await mock_get_order_status(order_id)
            response_message = f"Order {order_id}: Status {order_data['status']}, ETA {order_data['estimated_delivery']}." if order_data else f"Order ID {order_id} not found."
        else: response_message = "What's the order ID to track?"
    elif intent == "product_inquiry":
        product_name = entities.get("product_name")
        if product_name:
            product_data = await mock_get_product_info(product_name)
            response_message = f"Product '{product_name.title()}': Price {product_data['price']}, Stock: {'In stock' if product_data['in_stock'] else 'Out of stock'}." if product_data else f"Info for '{product_name}' not found."
        else: response_message = "Which product are you interested in?"
    elif intent == "request_return":
        response_message = "To start a return, please provide your order ID and the item you wish to return."
    elif intent == "request_refund":
        response_message = "For refunds, please tell me your order ID or refund reference number."
    elif intent == "account_issue":
        response_message = "For account issues, please visit [Your Site]/account-help."
    elif intent == "request_human_agent":
        response_message = "Understood. I'm connecting you to a human agent. Please wait."
        await _trigger_escalation("User requested human agent")
    elif intent == "other_fallback":
        # Count user fallbacks in this session (from in-memory log)
        user_fallback_count = sum(1 for log in chat_logs_db if log["session_id"] == session_id and log["sender"] == "user" and log["intent_classified"] == "other_fallback")
        if user_fallback_count >= 2: # Escalate after 2 user messages result in fallback
            response_message = "I'm still having trouble. Let me connect you to a human agent for better assistance."
            await _trigger_escalation("Bot fallback limit reached (2 consecutive fallbacks)")
        else:
            response_message = "I'm not sure how to help with that. Could you try rephrasing, or ask about orders, returns, or products?"

    # Log bot response (to in-memory list, replace with DB)
    chat_logs_db.append({
        "log_id": log_id_counter, "session_id": session_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sender": "bot", "message_text": response_message,
    })
    log_id_counter += 1

    return ChatResponse(
        session_id=session_id, response_message=response_message,
        escalated=escalated, escalation_ticket_id=escalation_ticket_id,
        debug_intent=intent, confidence=confidence
    )

# --- API Endpoints ---
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest): # BackgroundTasks removed for now, can be added back if needed
    session_id = request.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        chat_sessions_db[session_id] = { # Replace with DB
            "user_id": request.user_id, "start_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "end_time": None, "status": "active"
        }
    if session_id not in chat_sessions_db: # Handle if ID provided but not in mock DB
         chat_sessions_db[session_id] = {
            "user_id": request.user_id, "start_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "end_time": None, "status": "active"
        }
    try:
        response = await handle_chat_logic(session_id, request.message, request.user_id)
        return response
    except Exception as e:
        print(f"Critical error in /chat endpoint: {e}") # Log critical errors
        # Log error to chat_logs_db as well
        global log_id_counter
        chat_logs_db.append({
            "log_id": log_id_counter, "session_id": session_id or "unknown_session",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "sender": "system_error", "message_text": f"Internal error processing request: {str(e)}",
        })
        log_id_counter +=1
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

@app.post("/feedback", response_model=FeedbackResponse)
async def feedback_endpoint(request: FeedbackRequest):
    global feedback_id_counter
    feedback_entry = { # Replace with DB
        "feedback_id": feedback_id_counter, **request.model_dump(),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    feedback_db.append(feedback_entry)
    print(f"DEBUG: Feedback received and stored (in-memory): {feedback_entry}")
    current_feedback_id = feedback_id_counter
    feedback_id_counter += 1
    return FeedbackResponse(status="success", feedback_id=current_feedback_id)

@app.get("/health")
async def health_check():
    nlp_status = "loaded" if tokenizer and model else "not_loaded"
    redis_status = "connected" if redis_client and await redis_client.ping() else "disconnected"
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "nlp_model_status": nlp_status,
        "redis_status": redis_status
    }

if __name__ == "__main__":
    # To run: uvicorn main:app --reload --port 8000
    # Ensure Redis server is running.
    # Ensure NLP model can be downloaded by Hugging Face transformers.
    uvicorn.run(app, host="0.0.0.0", port=8000)
