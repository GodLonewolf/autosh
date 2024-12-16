import random
import uuid
import json
from urllib.parse import unquote

class Utils:
    @staticmethod
    def generate_random_string(length=8):
        """Generate a random alphanumeric string."""
        return ''.join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=length))

    @staticmethod
    def generate_uuid():
        """Generate a unique UUID."""
        return str(uuid.uuid4())

    @staticmethod
    def retry_request(session, method, url, retries=3, **kwargs):
        """Retry an HTTP request for a specific number of times."""
        for attempt in range(1, retries + 1):
            try:
                response = session.request(method, url, **kwargs)
                return response
            except Exception as e:
                print(f"Retry {attempt}/{retries} failed: {e}")
        return None

    @staticmethod
    def save_json(filename, data):
        """Save data to a JSON file."""
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def load_json(filename):
        """Load data from a JSON file."""
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    @staticmethod
    def convert_utf8_json(data):
        """Convert url encoded string to json"""
        return json.loads(unquote(data))

    @staticmethod
    def parse_between(text, start, end):
        return text.split(start)[1].split(end)[0]

    @staticmethod
    def get_cheapest_delivery(delivery):
        try:
            delivery_lines = delivery.get("deliveryLines", [])
            
            cheapest_handle = None
            cheapest_amount = float('inf')
            
            for line in delivery_lines:
                strategies = line.get("availableDeliveryStrategies", [])
                for strategy in strategies:
                    # Extract the amount value
                    amount = float(strategy["amount"]["value"]["amount"])
                    handle = strategy["handle"]
                    if amount < cheapest_amount:
                        cheapest_amount = amount
                        cheapest_handle = handle
            if cheapest_handle is not None:
                return {"handle": cheapest_handle, "amount": cheapest_amount}
            else:
                return {"error": "No delivery strategies found."}

        except Exception as e:
            return {"error": str(e)}