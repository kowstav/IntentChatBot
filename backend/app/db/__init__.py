# backend/app/db/__init__.py
from .models import Base # Assuming Base is defined in your models.py

# You can also re-export other common DB items if needed
# from .session import get_db
# from .schemas import Message, Conversation