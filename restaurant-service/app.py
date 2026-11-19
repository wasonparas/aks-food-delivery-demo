from flask import Flask, jsonify

app = Flask(__name__)
RESTAURANTS = [
    {"id": "rest-001", "name": "Kiwi Kitchen", "cuisine": "New Zealand", "rating": 4.7, "available": True},
    {"id": "rest-002", "name": "Spice Route", "cuisine": "Indian", "rating": 4.5, "available": True},
    {"id": "rest-003", "name": "Noodle House", "cuisine": "Asian", "rating": 4.3, "available": True},
]

@app.get("/health")
def health():
    return jsonify(status="healthy", service="restaurant-service")

@app.get("/restaurants")
def list_restaurants():
    return jsonify(items=RESTAURANTS, count=len(RESTAURANTS))

@app.get("/restaurants/<restaurant_id>")
def get_restaurant(restaurant_id):
    restaurant = next((r for r in RESTAURANTS if r["id"] == restaurant_id), None)
    if restaurant is None:
        return jsonify(error="restaurant_not_found", restaurant_id=restaurant_id), 404
    return jsonify(restaurant)

@app.get("/")
def index():
    return jsonify(message="Restaurant service is running", endpoints=["/restaurants", "/restaurants/<id>", "/health"])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
