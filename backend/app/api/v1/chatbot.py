from fastapi import APIRouter, Depends, HTTPException, WebSocket
from typing import Dict, Any
from ....core.nlp import process_message
from ....core.escalations import handle_escalation
from ....db.session import get_db
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(
    message: Dict[str, Any],
    db: Session = Depends(get_db)
):
    try:
        intent, confidence = process_message(message["text"])
        
        if confidence < settings.CONFIDENCE_THRESHOLD:
            ticket = handle_escalation(message, db)
            return {
                "response": f"Connecting you to a human agent. Ticket ID: {ticket.id}",
                "requires_human": True
            }
            
        response = generate_response(intent, message)
        return {"response": response, "requires_human": False}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            response = await chat_endpoint(data, db)
            await websocket.send_json(response)
    except Exception:
        await websocket.close()