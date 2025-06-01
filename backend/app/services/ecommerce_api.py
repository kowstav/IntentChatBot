# backend/app/services/ecommerce_api.py
# Mocked client for interacting with an external e-commerce platform's API.
import asyncio # For simulating async behavior

class MockEcommerceAPI:
    def __init__(self, api_key: str = "test_api_key_from_settings_or_default"):
        # In a real scenario, you might get the api_key from settings
        # from ..config import settings
        # self.api_key = api_key or settings.ECOMMERCE_API_KEY
        self.api_key = api_key
        
        self._mock_orders = {
            "12345": {"id": "12345", "status": "Shipped", "estimated_delivery": "2025-06-10", "items": ["SuperWidget", "MegaDongle"], "shipping_address": "123 Main St, Anytown, USA"},
            "67890": {"id": "67890", "status": "Processing", "estimated_delivery": "2025-06-12", "items": ["AwesomeGadget"], "shipping_address": "456 Oak Ave, Otherville, USA"},
            "ERROR01": {"error": "Invalid order ID format"},
            "77777": {"id": "77777", "status": "Delivered", "delivery_date": "2025-05-20", "items": ["HyperFlux Capacitor"], "shipping_address": "789 Pine Ln, Somewhere, USA"},
        }
        self._mock_products = {
            "SuperWidget": {"id": "SW001", "name": "SuperWidget", "price": 29.99, "in_stock": True, "description": "A truly super widget for all your needs.", "category": "Widgets"},
            "MegaDongle": {"id": "MD002", "name": "MegaDongle", "price": 15.50, "in_stock": True, "description": "The most mega dongle you will ever own.", "category": "Accessories"},
            "AwesomeGadget": {"id": "AG003", "name": "AwesomeGadget", "price": 99.00, "in_stock": False, "description": "An awesome gadget, currently out of stock. Expected restock: 2025-07-01.", "category": "Gadgets"},
            "HyperFlux Capacitor": {"id": "HFC004", "name": "HyperFlux Capacitor", "price": 1210.00, "in_stock": True, "description": "Powers time travel (theoretically).", "category": "Advanced Tech"},
            "Generic Product": {"id": "GP005", "name": "Generic Product", "price": 10.00, "in_stock": True, "description": "A standard product.", "category": "General"},
        }

    async def get_order_details(self, order_id: str) -> dict:
        print(f"MockEcommerceAPI: Fetching order details for '{order_id}' (API Key: {self.api_key})")
        await asyncio.sleep(0.15) # Simulate network latency
        if order_id in self._mock_orders:
            return self._mock_orders[order_id]
        return {"error": "Order not found", "order_id": order_id}

    async def get_product_info(self, product_name_query: str) -> dict:
        print(f"MockEcommerceAPI: Fetching product info for query '{product_name_query}'")
        await asyncio.sleep(0.1)
        for name, info in self._mock_products.items():
            if product_name_query.lower() in name.lower():
                return info
        return {"error": "Product not found", "query": product_name_query}

    async def request_return(self, order_id: str, item_name_or_sku: str, reason: str) -> dict:
        print(f"MockEcommerceAPI: Requesting return for item '{item_name_or_sku}' from order '{order_id}' due to '{reason}'")
        await asyncio.sleep(0.2)
        
        order = self._mock_orders.get(order_id)
        if not order or "error" in order:
            return {"error": "Order not found for return request.", "order_id": order_id}

        item_found_in_order = False
        for item in order.get("items", []):
            if item_name_or_sku.lower() in item.lower():
                item_found_in_order = True
                break
        
        if not item_found_in_order:
            return {"error": f"Item '{item_name_or_sku}' not found in order '{order_id}'.", "order_id": order_id, "item_sku": item_name_or_sku}

        # Simulate successful return initiation
        return_ticket_id = f"RET-{order_id}-{item_name_or_sku[:3].upper()}{random.randint(100,999)}"
        return {
            "return_ticket_id": return_ticket_id,
            "order_id": order_id,
            "item_returned": item_name_or_sku,
            "status": "Return initiated",
            "message": "Please check your email for a return shipping label and further instructions."
        }

    async def check_shipping_info(self, order_id: str) -> dict:
        print(f"MockEcommerceAPI: Checking shipping info for order '{order_id}'")
        await asyncio.sleep(0.1)
        order_details = self._mock_orders.get(order_id)
        if order_details and "error" not in order_details:
            if order_details["status"] == "Shipped":
                return {"order_id": order_id, "status": "Shipped", "tracking_number": f"1Z{order_id}FAKE TRACK", "estimated_delivery": order_details["estimated_delivery"]}
            elif order_details["status"] == "Delivered":
                return {"order_id": order_id, "status": "Delivered", "delivery_date": order_details["delivery_date"]}
            else:
                return {"order_id": order_id, "status": order_details["status"], "message": "Shipping information will be available once the order is shipped."}
        return {"error": "Order not found or shipping info unavailable.", "order_id": order_id}

# For direct testing of this module (optional)
if __name__ == '__main__':
    import random # Imported here as it's used above now
    
    async def main():
        mock_api = MockEcommerceAPI()
        
        print("\n--- Testing Order Details ---")
        print(await mock_api.get_order_details("12345"))
        print(await mock_api.get_order_details("00000")) # Not found
        
        print("\n--- Testing Product Info ---")
        print(await mock_api.get_product_info("SuperWidget"))
        print(await mock_api.get_product_info("Flux Capacitor")) # Partial match
        print(await mock_api.get_product_info("NonExistent"))
        
        print("\n--- Testing Return Request ---")
        print(await mock_api.request_return("12345", "SuperWidget", "Defective item"))
        print(await mock_api.request_return("12345", "NonExistentItem", "Wrong item"))
        print(await mock_api.request_return("00000", "SuperWidget", "Order not found"))

        print("\n--- Testing Shipping Info ---")
        print(await mock_api.check_shipping_info("12345")) # Shipped
        print(await mock_api.check_shipping_info("67890")) # Processing
        print(await mock_api.check_shipping_info("77777")) # Delivered
        print(await mock_api.check_shipping_info("00000")) # Not found

    asyncio.run(main())