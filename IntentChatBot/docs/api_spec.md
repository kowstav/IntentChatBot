# API Specification

## Chat Endpoints

### POST /api/v1/chat
Process a chat message and return response.

Request:
```json
{
  "text": "string",
  "user_id": "string" (optional)
}