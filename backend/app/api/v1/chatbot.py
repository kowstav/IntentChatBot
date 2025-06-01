# backend/app/api/v1/chatbot.py
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio # For potential async operations with services

from ....app.core.nlp import process_message
from ....app.core.escalations import handle_escalation
from ....app.db.session import get_db
from ....app.db import models, schemas
from ....app.config import settings
from ....app.services.ecommerce_api import MockEcommerceAPI # Import the mock service

router = APIRouter()

# Instantiate your mock e-commerce API client
# In a larger app, this might be managed via dependency injection
ecommerce_service = MockEcommerceAPI()

# --- Helper function to manage or create conversations and messages ---
# (Assuming the log_message_and_get_conversation from previous response is here)
# For brevity, I'll skip pasting it again but assume it's defined as before.
def log_message_and_get_conversation(db: Session, user_id: Optional[str], message_text: str, sender: str, intent: Optional[str] = None, confidence: Optional[float] = None, existing_conversation_id: Optional[int] = None) -> models.Conversation:
    db_conversation = None
    if existing_conversation_id:
        db_conversation = db.query(models.Conversation).filter(models.Conversation.id == existing_conversation_id).first()

    if not db_conversation:
        conversation_data = schemas.ConversationCreate(user_id=user_id)
        db_conversation = models.Conversation(**conversation_data.model_dump(), start_time=datetime.utcnow())
        db.add(db_conversation)
        db.commit() 
        db.refresh(db_conversation)
    
    message_data = schemas.MessageCreate(
        conversation_id=db_conversation.id,
        content=message_text,
        sender=sender,
        intent=intent,
        confidence=confidence
    )
    db_message = models.Message(**message_data.model_dump(), timestamp=datetime.utcnow())
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    return db_conversation

# --- Enhanced Response Generation with Business Logic ---
async def generate_bot_response(intent: str, confidence: float, message_text: str, entities: Dict[str, Any], db: Session, conversation_id: int, user_id: Optional[str] = None) -> str:
    """
    Generates a bot response based on intent, entities, and e-commerce service interactions.
    """
    response_text = f"I'm not sure how to help with that. (Intent: {intent})" # Default fallback

    if intent == "greet":
        response_text = random.choice(["Hello! How can I assist you today?", "Hi there! What can I do for you?", "Hey! How may I help?"])
    
    elif intent == "goodbye":
        response_text = random.choice(["Goodbye! Have a great day.", "Thanks for chatting!", "See you later!"])

    elif intent == "track_order":
        order_id = entities.get("order_id")
        if order_id:
            order_details = await ecommerce_service.get_order_details(order_id)
            if "error" not in order_details:
                response_text = f"Order {order_id}: Status is '{order_details.get('status', 'N/A')}'."
                if order_details.get('estimated_delivery'):
                    response_text += f" Estimated delivery: {order_details['estimated_delivery']}."
            else:
                response_text = f"Sorry, I couldn't find details for order ID '{order_id}'. {order_details.get('error', 'Please check the ID and try again.')}"
        else:
            response_text = "I can help you track an order. What is your order ID, please?"

    elif intent == "product_info":
        product_query = entities.get("product_name_query")
        if product_query:
            product_details = await ecommerce_service.get_product_info(product_query)
            if "error" not in product_details:
                response_text = f"Regarding '{product_details.get('name', product_query)}': {product_details.get('description', 'No description available.')} Price: ${product_details.get('price', 'N/A')}. Currently {'in stock' if product_details.get('in_stock') else 'out of stock'}."
            else:
                response_text = f"I couldn't find information about '{product_query}'. Could you be more specific or try a different product name?"
        else:
            response_text = "Sure, I can look up product information. Which product are you interested in?"

    elif intent == "price_query":
        product_query = entities.get("product_name_query")
        if product_query:
            product_details = await ecommerce_service.get_product_info(product_query) # Reuse product info
            if "error" not in product_details and product_details.get('price') is not None:
                response_text = f"The price for '{product_details.get('name', product_query)}' is ${product_details['price']}."
            elif "error" not in product_details:
                 response_text = f"I found info for '{product_details.get('name', product_query)}' but couldn't find specific pricing. You can check its details on the product page."
            else:
                response_text = f"I couldn't find pricing for '{product_query}'. Please try another product name."
        else:
            response_text = "Which product's price are you interested in?"

    elif intent == "availability":
        product_query = entities.get("product_name_query")
        if product_query:
            product_details = await ecommerce_service.get_product_info(product_query) # Reuse product info
            if "error" not in product_details:
                status = 'in stock' if product_details.get('in_stock') else 'out of stock'
                response_text = f"'{product_details.get('name', product_query)}' is currently {status}."
            else:
                response_text = f"I couldn't check availability for '{product_query}'. Please try another product name."
        else:
            response_text = "Which product's availability would you like to check?"
            
    elif intent == "request_return":
        order_id = entities.get("order_id")
        item_sku = entities.get("item_sku") # Assuming NLP might extract this
        
        if not order_id:
            response_text = "I can help with returns. What is your order ID?"
        elif not item_sku: # If order_id is present but not item
             response_text = f"For order {order_id}, which item would you like to return? Please provide the item name or SKU."
        else: # If both order_id and item_sku are present (ideal case from user query)
            # For simplicity, let's assume a generic reason or that it's part of message_text
            reason_for_return = "User requested via chatbot" 
            return_status = await ecommerce_service.request_return(order_id, item_sku, reason_for_return)
            if "error" not in return_status:
                response_text = f"Return request for item '{item_sku}' from order '{order_id}' {return_status.get('status', 'processed')}. {return_status.get('message', '')}"
            else:
                response_text = f"Sorry, I couldn't process the return for item '{item_sku}' from order '{order_id}'. {return_status.get('error', 'Please contact support directly.')}"
                
    elif intent == "shipping_info":
        # This could be a more complex interaction, asking about specific order or general policy
        order_id = entities.get("order_id")
        if order_id:
             # Delegate to track_order logic for now if an order_id is present
             # Or fetch specific shipping details if your e-commerce API supports it separately
            order_details = await ecommerce_service.get_order_details(order_id)
            if "error" not in order_details and order_details.get('status') == "Shipped":
                 response_text = f"Order {order_id} has shipped. Estimated delivery: {order_details.get('estimated_delivery', 'N/A')}. For more details, please check your tracking number."
            elif "error" not in order_details:
                 response_text = f"Order {order_id} is currently {order_details.get('status', 'being processed')}. Standard shipping times apply once it ships."
            else:
                 response_text = f"I couldn't find shipping info for order {order_id}. You can also check our general shipping policies on the website."
        else:
            response_text = "Are you asking about shipping for a specific order, or our general shipping policies?"

    elif intent == "human_agent":
        # This case is typically handled by the escalation logic before this function is called.
        # If it reaches here, it means the confidence was high for "human_agent" but threshold logic didn't catch it for escalation.
        response_text = "I see you'd like to speak to a human agent. I'll escalate this for you."
        # The main endpoint logic should catch this intent and trigger escalation.

    elif intent == "general_query" or intent == "empty_message":
        response_text = "I'm here to help with orders, products, returns, and shipping. How can I assist you today?"
        if confidence < 0.3 and intent != "empty_message": # Very low confidence for something specific
            response_text = "I'm not quite sure what you mean. Could you please rephrase your question?"

    # Log the bot's response message (this is also done in the calling endpoint function)
    # log_message_and_get_conversation(db, user_id, response_text, "bot", existing_conversation_id=conversation_id)
    return response_text


@router.post("/chat")
async def http_chat_endpoint(
    payload: Dict[str, Any], 
    db: Session = Depends(get_db)
):
    user_text = payload.get("text")
    user_id = payload.get("user_id")
    # conversation_id might be passed in payload if client manages it for HTTP sessions
    # current_conversation_id = payload.get("conversation_id") 

    if not user_text:
        raise HTTPException(status_code=400, detail="Text input cannot be empty")

    # Log user message & manage conversation context
    # For HTTP, this simplified version creates/uses a conversation per call if no ID is passed.
    # A more robust HTTP chat would involve the client sending a session_id.
    active_conversation = log_message_and_get_conversation(db, user_id, user_text, "user")
    
    intent, confidence, entities = process_message(user_text)

    # Update user's message log with intent and confidence
    # (This requires finding the last message by this user in this conversation and updating it,
    # or modifying log_message_and_get_conversation to accept intent/confidence for user messages)
    # For simplicity, we'll assume the initial log by log_message_and_get_conversation is sufficient for now,
    # or that function is enhanced to store intent for user messages.

    response_payload = {
        "conversation_id": active_conversation.id,
        "intent": intent,
        "confidence": confidence,
        "entities": entities, # Send back extracted entities
        "requires_human_escalation": False,
    }

    if confidence < settings.CONFIDENCE_THRESHOLD or intent == "human_agent":
        ticket = handle_escalation(user_text, user_id, db, conversation_id=active_conversation.id)
        bot_response_text = f"I'm not quite sure how to best assist with that, or you've requested help. I'm connecting you to a human agent. Your Ticket ID is: {ticket.id}"
        response_payload["response"] = bot_response_text
        response_payload["requires_human_escalation"] = True
        response_payload["escalation_ticket_id"] = ticket.id
    else:
        bot_response_text = await generate_bot_response(intent, confidence, user_text, entities, db, active_conversation.id, user_id)
        response_payload["response"] = bot_response_text
            
    log_message_and_get_conversation(db, user_id, bot_response_text, "bot", existing_conversation_id=active_conversation.id)
    
    return response_payload


# Keep track of active WebSocket connections (conversation_id -> WebSocket)
active_connections: Dict[int, WebSocket] = {} # Should ideally be stored in Redis for scalability

@router.websocket("/ws")
async def websocket_chat_endpoint(websocket: WebSocket, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    await websocket.accept()
    db_conversation = log_message_and_get_conversation(db, user_id, "User connected via WebSocket.", "system")
    conversation_id = db_conversation.id
    active_connections[conversation_id] = websocket
    print(f"WebSocket connected for conversation_id: {conversation_id}, user_id: {user_id}")

    try:
        while True:
            data = await websocket.receive_json()
            user_text = data.get("text")

            if not user_text:
                await websocket.send_json({"error": "Text input cannot be empty", "conversation_id": conversation_id})
                continue

            log_message_and_get_conversation(db, user_id, user_text, "user", existing_conversation_id=conversation_id)
            intent, confidence, entities = process_message(user_text)
            
            response_payload = {
                "conversation_id": conversation_id,
                "intent": intent,
                "confidence": confidence,
                "entities": entities,
                "requires_human_escalation": False,
                "text_received": user_text # Echo back what was received, for clarity
            }

            if confidence < settings.CONFIDENCE_THRESHOLD or intent == "human_agent":
                ticket = handle_escalation(user_text, user_id, db, conversation_id=conversation_id)
                bot_response_text = f"Connecting you to a human agent. Your Ticket ID: {ticket.id}"
                response_payload["response"] = bot_response_text
                response_payload["requires_human_escalation"] = True
                response_payload["escalation_ticket_id"] = ticket.id
            else:
                bot_response_text = await generate_bot_response(intent, confidence, user_text, entities, db, conversation_id, user_id)
                response_payload["response"] = bot_response_text
            
            log_message_and_get_conversation(db, user_id, bot_response_text, "bot", existing_conversation_id=conversation_id)
            await websocket.send_json(response_payload)

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for conversation_id: {conversation_id}")
        db_conv = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
        if db_conv and not db_conv.end_time: # Mark conversation as ended if not already
            db_conv.end_time = datetime.utcnow()
            db.commit()
    except Exception as e:
        print(f"Error in WebSocket for conversation {conversation_id}: {e}")
        try:
            await websocket.send_json({"error": str(e), "conversation_id": conversation_id})
        except: # If sending fails too
            pass 
    finally:
        if conversation_id in active_connections:
            del active_connections[conversation_id]