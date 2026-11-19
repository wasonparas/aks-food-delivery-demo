import os
import uuid
from flask import Flask, jsonify, request

app = Flask(__name__)
EXPECTED_API_KEY = os.getenv("PAYMENT_API_KEY", "change-me")

@app.get("/health")
def health():
    return jsonify(status="healthy", service="payment-service")

@app.post("/payments/charge")
def charge():
    if request.headers.get("X-Demo-Key") != EXPECTED_API_KEY:
        return jsonify(error="unauthorized", message="A valid X-Demo-Key header is required"), 401
    data = request.get_json(silent=True) or {}
    order_id = data.get("order_id")
    amount = data.get("amount")
    currency = data.get("currency", "NZD")
    if not order_id or not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify(error="invalid_request", message="Provide order_id and a positive numeric amount"), 400
    # Demo only: no real payment gateway or money movement is involved.
    return jsonify(payment_id=f"pay-{uuid.uuid4().hex[:10]}", order_id=order_id, amount=amount, currency=currency, status="APPROVED", simulated=True), 201

@app.get("/")
def index():
    return jsonify(message="Payment service is running. Payments are simulated.", endpoints=["POST /payments/charge", "/health"])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082)
