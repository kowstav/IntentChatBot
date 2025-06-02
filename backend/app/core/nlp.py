
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from typing import Tuple, Dict, Any, List # Added List
from ..config import settings

class IntentClassifier:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(settings.MODEL_NAME)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            settings.MODEL_NAME,
            num_labels=len(self.get_intent_labels())
        )
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval() # Ensure model is in evaluation mode
        
    @staticmethod
    def get_intent_labels() -> List[str]: # Added List type hint
        return [
            "track_order",
            "request_return",
            "product_info",
            "shipping_info", # New intent based on common e-commerce queries
            "price_query",   # New intent
            "availability",  # New intent
            "human_agent",   # User wants to speak to a human
            "general_query", # A fallback or general question
            "greet",         # Greeting intent
            "goodbye"        # Goodbye intent
        ]
    
    def predict(self, text: str) -> Tuple[str, float, Dict[str, Any]]:
        inputs = self.tokenizer(
            text,
            truncation=True,
            padding=True,
            max_length=512, # Added max_length for robustness
            return_tensors="pt"
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=1)
            confidence_tensor, predicted_class_tensor = torch.max(probabilities, dim=1)
            
        intent = self.get_intent_labels()[predicted_class_tensor.item()]
        confidence = confidence_tensor.item()
        
        entities = {}
        text_lower = text.lower()

        if intent == "track_order":
            import re
            match = re.search(r'\b(\d{5,})\b', text) # Look for 5 or more digits
            if match:
                entities["order_id"] = match.group(1)
            else: # Try to find alphanumeric order IDs (e.g., ORD123XYZ)
                match_alnum = re.search(r'\b([a-zA-Z0-9]{6,}-[a-zA-Z0-9]{6,}|[a-zA-Z]{2,}\d{4,})\b', text)
                if match_alnum:
                    entities["order_id"] = match_alnum.group(1)

        elif intent == "product_info" or intent == "price_query" or intent == "availability":
            # Very basic: assumes product name might be after certain phrases
            keywords_to_remove = [
                "tell me about", "info on", "product info for", "is", "in stock",
                "how much is", "price of", "availability of", "check if", "available",
                "the", "a", "an", "for"
            ]

            temp_message = text_lower
            for kw in keywords_to_remove:
                temp_message = temp_message.replace(kw, "")
            # Remove question marks
            temp_message = temp_message.replace("?","").strip()
            if temp_message: # If anything is left, consider it a potential product name
                entities["product_name_query"] = temp_message
        
        elif intent == "request_return":
            import re
            # Try to find an order ID if mentioned with return
            match = re.search(r'\b(\d{5,})\b', text)
            if match:
                entities["order_id"] = match.group(1)
            #  might also look for item names here if the query is complex

        return intent, confidence, entities


try:
    classifier = IntentClassifier()
    print("IntentClassifier initialized successfully.")
except Exception as e:
    print(f"Error initializing IntentClassifier: {e}")
    print("NLP features will be severely limited. Check model name and availability.")
    # Fallback classifier if initialization fails
    class FallbackClassifier:
        def predict(self, text: str) -> Tuple[str, float, Dict[str, Any]]:
            return "general_query", 0.1, {} # Low confidence fallback
    classifier = FallbackClassifier()


def process_message(text: str) -> Tuple[str, float, Dict[str, Any]]:
    if not text or not text.strip():
        return "empty_message", 1.0, {} # Handle empty input gracefully
    return classifier.predict(text)