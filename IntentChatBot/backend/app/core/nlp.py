from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from typing import Tuple
from ..config import settings
import numpy as np

class IntentClassifier:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(settings.MODEL_NAME)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            settings.MODEL_NAME,
            num_labels=len(self.get_intent_labels())
        )
        
        # Move model to GPU if available
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        
    @staticmethod
    def get_intent_labels():
        return [
            "track_order",
            "request_return",
            "product_info",
            "shipping_info",
            "price_query",
            "availability",
            "human_agent",
            "general_query"
        ]
    
    def predict(self, text: str) -> Tuple[str, float]:
        inputs = self.tokenizer(
            text,
            truncation=True,
            padding=True,
            return_tensors="pt"
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=1)
            confidence, predicted_class = torch.max(probabilities, dim=1)
            
        intent = self.get_intent_labels()[predicted_class.item()]
        return intent, confidence.item()

# Initialize global classifier
classifier = IntentClassifier()

def process_message(text: str) -> Tuple[str, float]:
    return classifier.predict(text)