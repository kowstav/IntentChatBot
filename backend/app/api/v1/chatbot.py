# backend/app/api/v1/chatbot.py
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio # For potential async operations with services
import random # Import random

from ....app.core.nlp import process_message
from ....app.core.escalations import handle_escalation # Assuming create_escalation_ticket is also used or part of it
from ....app.db.session import get_db
from ....app.db import models, schemas
from ....app.config import settings
from ....app.services.ecommerce_api import MockEcommerceAPI # Import the mock service

router = APIRouter()
ecommerce_service = MockEcommerceAPI()

# --- Helper function to manage or create conversations and log messages ---
def get_or_create_conversation(db: Session, user_id: Optional[str], conversation_id: Optional[int] = None) -> models.Conversation:
    db_conversation = None
    if conversation_id:
        db_conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()

    if not db_conversation:
        conversation_data = schemas.ConversationCreate(user_id=user_id)
        db_conversation = models.Conversation(**conversation_data.model_dump(), start_time=datetime.utcnow())
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
    return db_conversation

def log_message(db: Session, conversation_id: int, text: str, sender: str, intent: Optional[str] = None, confidence: Optional[float] = None) -> models.Message:
    message_data = schemas.MessageCreate(
        conversation_id=conversation_id,
        content=text,
        sender=sender,
        intent=intent,
        confidence=confidence
    )
    db_message = models.Message(**message_data.model_dump(), timestamp=datetime.utcnow())
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

# --- Enhanced Response Generation with Business Logic ---
async def generate_bot_response(
    intent: str,
    confidence: float,
    message_text: str, # User's original message text
    entities: Dict[str, Any],
    db: Session, # Keep db session if needed for complex response generation (e.g. fetching history)
    conversation_id: int, # Keep for context
    user_id: Optional[str] = None # Keep for context
) -> str:
    response_text = f"I'm not sure how to help with that. (Intent: {intent})"

    if intent == "greet":
        response_text = random.choice(["Hello! How can I assist  today?", "Hi there! What can I do for ?", "Hey! How may I help?"])
    
    elif intent == "goodbye":
        response_text = random.choice(["Goodbye! Have a great day.", "Thanks for chatting!", "See  later!"])

    elif intent == "track_order":
        order_id = entities.get("order_id")
        if order_id:
            order_details = await ecommerce_service.get_order_details(order_id)
            if "error" not in order_details:
                response_text = f"Order {order_id}: Status is '{order_details.get('status', 'N/A')}'."
                if order_details.get('estimated_delivery'):
                    response_text += f" Estimated delivery: {order_details['estimated_delivery']}."
                if order_details.get('status') == "Delivered" and order_details.get('delivery_date'):
                     response_text += f" Delivered on: {order_details['delivery_date']}."
            else:
                response_text = f"Sorry, I couldn't find details for order ID '{order_id}'. {order_details.get('error', 'Please check the ID and try again.')}"
        else:
            response_text = "I can help  track an order. What is the order ID, please?"

    elif intent == "product_info":
        product_query = entities.get("product_name_query")
        if product_query:
            product_details = await ecommerce_service.get_product_info(product_query)
            if "error" not in product_details:
                response_text = f"Regarding '{product_details.get('name', product_query)}': {product_details.get('description', 'No description available.')} Price: ${product_details.get('price', 'N/A'):.2f}. Currently {'in stock' if product_details.get('in_stock') else 'out of stock'}."
                if not product_details.get('in_stock') and "Expected restock" in product_details.get('description',''):
                    response_text += f" {product_details.get('description').split('Expected restock:')[1].strip()}"
            else:
                response_text = f"I couldn't find information about '{product_query}'. Could  be more specific or try a different product name?"
        else:
            response_text = "Sure, I can look up product information. Which product are  interested in?"

    elif intent == "price_query":
        product_query = entities.get("product_name_query")
        if product_query:
            product_details = await ecommerce_service.get_product_info(product_query)
            if "error" not in product_details and product_details.get('price') is not None:
                response_text = f"The price for '{product_details.get('name', product_query)}' is ${product_details['price']:.2f}."
            elif "error" not in product_details:
                 response_text = f"I found info for '{product_details.get('name', product_query)}' but couldn't find specific pricing.  can check its details on the product page."
            else:
                response_text = f"I couldn't find pricing for '{product_query}'. Please try another product name."
        else:
            response_text = "Which product's price are  interested in?"

    elif intent == "availability":
        product_query = entities.get("product_name_query")
        if product_query:
            product_details = await ecommerce_service.get_product_info(product_query)
            if "error" not in product_details:
                status = 'in stock' if product_details.get('in_stock') else 'out of stock'
                response_text = f"'{product_details.get('name', product_query)}' is currently {status}."
                if not product_details.get('in_stock') and "Expected restock" in product_details.get('description',''):
                    response_text += f" Expected restock: {product_details.get('description').split('Expected restock:')[1].strip()}"
            else:
                response_text = f"I couldn't check availability for '{product_query}'. Please try another product name."
        else:
            response_text = "Which product's availability would  like to check?"
            
    elif intent == "request_return":
        order_id = entities.get("order_id")
        # Assuming NLP might extract item_sku or product_name_query for the item to be returned
        item_query = entities.get("item_sku") or entities.get("product_name_query") # More flexible entity check
        
        if not order_id:
            response_text = "I can help with returns. What is the order ID?"
        elif not item_query:
             response_text = f"For order {order_id}, which item would  like to return? Please provide the item name or SKU."
        else:
            reason_for_return = f"User requested return for '{item_query}' via chatbot from order {order_id}. Original message: {message_text}"
            return_status = await ecommerce_service.request_return(order_id, item_query, reason_for_return)
            if "error" not in return_status:
                response_text = (f"Return request for item '{return_status.get('item_returned', item_query)}' from order '{order_id}' {return_status.get('status', 'processed')}. "
                                 f"Ticket ID: {return_status.get('return_ticket_id')}. {return_status.get('message', '')}")
            else:
                response_text = f"Sorry, I couldn't process the return for item '{item_query}' from order '{order_id}'. {return_status.get('error', 'Please contact support directly.')}"
                
    elif intent == "shipping_info":
        order_id = entities.get("order_id")
        if order_id:
            shipping_details = await ecommerce_service.check_shipping_info(order_id)
            if "error" not in shipping_details:
                response_text = f"Shipping status for order {order_id}: {shipping_details.get('status')}."
                if shipping_details.get('tracking_number'):
                    response_text += f" Tracking: {shipping_details['tracking_number']}."
                if shipping_details.get('estimated_delivery'):
                    response_text += f" Estimated delivery: {shipping_details['estimated_delivery']}."
                if shipping_details.get('delivery_date'):
                    response_text += f" Delivered on: {shipping_details['delivery_date']}."
                if shipping_details.get('message'):
                    response_text += f" {shipping_details['message']}"
            else:
                 response_text = f"I couldn't find shipping info for order {order_id}. {shipping_details.get('error', 'Please check the ID.')}  can also check our general shipping policies on the website."
        else:
            response_text = (" can ask about shipping for a specific order (please provide the Order ID) "
                             "or about our general shipping policies (e.g., 'What are the shipping times?').")

    elif intent == "human_agent":
        response_text = "I understand 'd like to speak to a human agent. I'm escalating this for  now."
        # Actual escalation is handled by the main endpoint logic

    elif intent == "general_query" or intent == "empty_message":
        response_text = "I'm here to help with orders, products, returns, and shipping. How can I assist  today?"
        if confidence < 0.3 and intent != "empty_message": 
            response_text = "I'm not quite sure what  mean. Could  please rephrase the question or ask for 'help'?"

    return response_text

# Model for HTTP Chat Payload
class ChatPayload(schemas.BaseModel):
    text: str
    user_id: Optional[str] = None
    conversation_id: Optional[int] = None # Client can send this to continue a conversation

@router.post("/chat", response_model=schemas.ChatResponse) # Define a response model
async def http_chat_endpoint(
    payload: ChatPayload, 
    db: Session = Depends(get_db)
):
    if not payload.text:
        raise HTTPException(status_code=400, detail="Text input cannot be empty")

    active_conversation = get_or_create_conversation(db, payload.user_id, payload.conversation_id)
    
    # Log user message BEFORE NLP processing
    user_db_message = log_message(db, active_conversation.id, payload.text, "user")
    
    intent, confidence, entities = process_message(payload.text)

    # Update user's message in DB with NLP results
    user_db_message.intent = intent
    user_db_message.confidence = confidence
    db.commit()
    db.refresh(user_db_message)

    response_payload = {
        "conversation_id": active_conversation.id,
        "user_message_id": user_db_message.id, # Send back user message ID
        "intent": intent,
        "confidence": confidence,
        "entities": entities,
        "requires_human_escalation": False,
        "response": "", # Initialize response
        "bot_message_id": None # Initialize
    }

    if confidence < settings.CONFIDENCE_THRESHOLD or intent == "human_agent":
        ticket = handle_escalation(payload.text, payload.user_id, db, conversation_id=active_conversation.id)
        bot_response_text = f"I'm not quite sure how to best assist with that, or 've requested help. I'm connecting  to a human agent. the Ticket ID is: {ticket.id}"
        response_payload["response"] = bot_response_text
        response_payload["requires_human_escalation"] = True
        response_payload["escalation_ticket_id"] = ticket.id
    else:
        bot_response_text = await generate_bot_response(intent, confidence, payload.text, entities, db, active_conversation.id, payload.user_id)
        response_payload["response"] = bot_response_text
            
    bot_db_message = log_message(db, active_conversation.id, bot_response_text, "bot", intent if intent != "human_agent" and confidence >= settings.CONFIDENCE_THRESHOLD else "bot_response", 1.0)
    response_payload["bot_message_id"] = bot_db_message.id
    
    return response_payload

# One conversation can have multiple client connections (e.g. user refreshes tab)
active_connections: Dict[int, List[WebSocket]] = {} 

@router.websocket("/ws")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    user_id: Optional[str] = Query(None), # Allow user_id as query param
    conversation_id_query: Optional[int] = Query(None, alias="conversationId"), # Allow conversation_id as query param
    db: Session = Depends(get_db)
):
    await websocket.accept()
    
    # Determine conversation: use existing if ID provided and valid, else create new
    active_conversation = get_or_create_conversation(db, user_id, conversation_id_query)
    conversation_id = active_conversation.id

    if conversation_id not in active_connections:
        active_connections[conversation_id] = []
    active_connections[conversation_id].append(websocket)
    
    print(f"WebSocket connected for conversation_id: {conversation_id}, user_id: {user_id}. Total connections for this convo: {len(active_connections[conversation_id])}")

    # Send initial connection confirmation with conversation_id
    await websocket.send_json({"type": "connection_ack", "conversation_id": conversation_id, "message": "Connected to chatbot."})

    try:
        while True:
            data = await websocket.receive_json()
            user_text = data.get("text")
            client_conversation_id = data.get("conversation_id")

            if not user_text:
                await websocket.send_json({"error": "Text input cannot be empty", "conversation_id": conversation_id})
                continue
            
            # Ensure messages are logged to the correct conversation if client sends an ID
            current_processing_conv_id = client_conversation_id if client_conversation_id and client_conversation_id == conversation_id else conversation_id

            # Log user message before NLP
            user_db_message = log_message(db, current_processing_conv_id, user_text, "user")
            intent, confidence, entities = process_message(user_text)

            # Update user's message in DB with NLP results
            user_db_message.intent = intent
            user_db_message.confidence = confidence
            db.commit()
            db.refresh(user_db_message)
            
            response_data = {
                "conversation_id": current_processing_conv_id,
                "user_message_id": user_db_message.id,
                "intent": intent,
                "confidence": confidence,
                "entities": entities,
                "requires_human_escalation": False,
                "text_received": user_text,
                "response": "",
                "bot_message_id": None
            }

            if confidence < settings.CONFIDENCE_THRESHOLD or intent == "human_agent":
                ticket = handle_escalation(user_text, user_id, db, conversation_id=current_processing_conv_id)
                bot_response_text = f"Connecting  to a human agent. the Ticket ID: {ticket.id}"
                response_data["response"] = bot_response_text
                response_data["requires_human_escalation"] = True
                response_data["escalation_ticket_id"] = ticket.id
            else:
                bot_response_text = await generate_bot_response(intent, confidence, user_text, entities, db, current_processing_conv_id, user_id)
                response_data["response"] = bot_response_text
            
            bot_db_message = log_message(db, current_processing_conv_id, bot_response_text, "bot", intent if intent != "human_agent" and confidence >= settings.CONFIDENCE_THRESHOLD else "bot_response", 1.0)
            response_data["bot_message_id"] = bot_db_message.id
            
            await websocket.send_json(response_data)

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for conversation_id: {conversation_id}")
    except Exception as e:
        print(f"Error in WebSocket for conversation {conversation_id}: {type(e).__name__} - {e}")
        try:
            await websocket.send_json({"error": str(e), "type": "error", "conversation_id": conversation_id})
        except Exception as send_e:
            print(f"Failed to send error to WebSocket: {send_e}")
            pass 
    finally:
        if conversation_id in active_connections:
            active_connections[conversation_id].remove(websocket)
            if not active_connections[conversation_id]:
                del active_connections[conversation_id]
        print(f"Cleaned up WebSocket connection for conversation_id: {conversation_id}. Remaining for convo: {len(active_connections.get(conversation_id, []))}")