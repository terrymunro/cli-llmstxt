"""
A simple Flask application for testing the repository analyzer.
"""

from flask import Flask, jsonify, request

app = Flask(__name__)

items = [
    {"id": 1, "name": "Item 1", "description": "This is item 1"},
    {"id": 2, "name": "Item 2", "description": "This is item 2"},
    {"id": 3, "name": "Item 3", "description": "This is item 3"},
]


@app.route("/api/items", methods=["GET"])
def get_items():
    """
    Get all items.

    Returns:
        JSON: List of all items.
    """
    return jsonify(items)


@app.route("/api/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    """
    Get a specific item by ID.

    Args:
        item_id (int): ID of the item to retrieve.

    Returns:
        JSON: Item data if found, error message otherwise.
    """
    item = next((item for item in items if item["id"] == item_id), None)
    if item:
        return jsonify(item)
    return jsonify({"error": "Item not found"}), 404


@app.route("/api/items", methods=["POST"])
def create_item():
    """
    Create a new item.

    Request body:
        JSON: Item data with name and description.

    Returns:
        JSON: Created item data.
    """
    data = request.json
    if not data or not data.get("name") or not data.get("description"):
        return jsonify({"error": "Name and description are required"}), 400

    new_id = max(item["id"] for item in items) + 1
    new_item = {"id": new_id, "name": data["name"], "description": data["description"]}
    items.append(new_item)
    return jsonify(new_item), 201


@app.route("/api/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    """
    Update an existing item.

    Args:
        item_id (int): ID of the item to update.

    Request body:
        JSON: Updated item data.

    Returns:
        JSON: Updated item data if found, error message otherwise.
    """
    item = next((item for item in items if item["id"] == item_id), None)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "name" in data:
        item["name"] = data["name"]
    if "description" in data:
        item["description"] = data["description"]

    return jsonify(item)


@app.route("/api/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    """
    Delete an item.

    Args:
        item_id (int): ID of the item to delete.

    Returns:
        JSON: Success message if found, error message otherwise.
    """
    global items
    initial_count = len(items)
    items = [item for item in items if item["id"] != item_id]

    if len(items) < initial_count:
        return jsonify({"message": "Item deleted successfully"})
    return jsonify({"error": "Item not found"}), 404


if __name__ == "__main__":
    app.run(debug=True)
