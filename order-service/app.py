import os
import uuid
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
RESTAURANT_SERVICE_URL = os.getenv("RESTAURANT_SERVICE_URL", "http://restaurant-service:8080")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8082")
PAYMENT_API_KEY = os.getenv("PAYMENT_API_KEY", "")

@app.get("/health")
def health():
    return jsonify(status="healthy", service="order-service")

@app.post("/orders")
def create_order():
    data = request.get_json(silent=True) or {}
    restaurant_id = data.get("restaurant_id")
    item = data.get("item")
    amount = data.get("amount")
    customer = data.get("customer", "Demo Customer")
    if not restaurant_id or not item or not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify(error="invalid_request", message="Provide restaurant_id, item and a positive numeric amount"), 400

    try:
        restaurant_response = requests.get(f"{RESTAURANT_SERVICE_URL}/restaurants/{restaurant_id}", timeout=3)
        if restaurant_response.status_code == 404:
            return jsonify(error="restaurant_not_found", restaurant_id=restaurant_id), 404
        restaurant_response.raise_for_status()
        restaurant = restaurant_response.json()
    except requests.RequestException as exc:
        app.logger.exception("Restaurant service request failed")
        return jsonify(error="restaurant_service_unavailable", detail=str(exc)), 502

    order_id = f"ord-{uuid.uuid4().hex[:10]}"
    try:
        payment_response = requests.post(
            f"{PAYMENT_SERVICE_URL}/payments/charge",
            json={"order_id": order_id, "amount": amount, "currency": "NZD"},
            headers={"X-Demo-Key": PAYMENT_API_KEY},
            timeout=4,
        )
        payment_response.raise_for_status()
        payment = payment_response.json()
    except requests.RequestException as exc:
        app.logger.exception("Payment service request failed")
        return jsonify(error="payment_service_unavailable", detail=str(exc)), 502

    return jsonify(
        order_id=order_id,
        status="CONFIRMED",
        customer=customer,
        restaurant=restaurant["name"],
        item=item,
        amount=amount,
        currency="NZD",
        payment=payment,
    ), 201

@app.get("/orders")
def list_orders():
    return jsonify(message="This demo does not persist orders. POST /orders to create one.", items=[])

@app.get("/")
def index():
    return jsonify(message="Order service is running", endpoints=["POST /orders", "GET /orders", "/health"])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
