from datetime import datetime
from flask import Flask, request, jsonify
from flask_migrate import Migrate
from flask_restful import Api, Resource
from werkzeug.exceptions import NotFound
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from models import MenuItem, Order, OrderItem, User, db  # Import only necessary models and db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)  # Allow requests from all origins

db.init_app(app)
migrate = Migrate(app, db)

api = Api(app)

# Views go here

@app.route('/')
def index():
    return 'Welcome to your Flask App!'

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password, password):
        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role
        }), 200
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/menu', methods=['GET', 'POST'])
def handle_menu_items():
    if request.method == 'GET':
        menu_items = MenuItem.query.all()
        return jsonify([item.to_dict() for item in menu_items])
    
    elif request.method == 'POST':
        data = request.json
        if not data or 'name' not in data or 'price' not in data:
            return jsonify({"error": "Invalid data. 'name' and 'price' are required."}), 400
        
        new_menu_item = MenuItem(
            name=data['name'],
            price=data['price'],
            description=data.get('description'),
            image=data.get('image')  # Ensure image is included if provided
        )

        db.session.add(new_menu_item)
        db.session.commit()

        return jsonify({"message": "Menu item created successfully.", "menu_item": new_menu_item.to_dict()}), 201

@app.route('/menu/<int:id>', methods=['GET', 'DELETE'])
def handle_menu_item(id):
    menu_item = MenuItem.query.get(id)
    if not menu_item:
        raise NotFound("Menu item not found")
    
    if request.method == 'GET':
        return jsonify(menu_item.to_dict())
    
    elif request.method == 'DELETE':
        db.session.delete(menu_item)
        db.session.commit()
        return jsonify({"message": "Menu item deleted successfully"})

@app.route('/api/orders', methods=['GET'])
def get_orders():
    try:
        orders = Order.query.all()
        orders_list = [order.to_dict(include_order_items=True) for order in orders]
        return jsonify(orders_list), 200
    except Exception as e:
        app.logger.error(f"Error fetching orders: {e}")
        return jsonify({"error": "Failed to fetch orders"}), 500

@app.route('/api/orders/<int:id>', methods=['GET'])
def get_order(id):
    try:
        order = Order.query.get(id)
        if not order:
            return jsonify({"error": "Order not found"}), 404

        order_data = order.to_dict(include_order_items=True)
        return jsonify(order_data), 200
    except Exception as e:
        app.logger.error(f"Error fetching order: {e}")
        return jsonify({"error": "Failed to fetch order"}), 500

@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        order_items = data.get('order_items', [])  # Default to empty list if not provided

        if not user_id or not order_items:
            raise ValueError("Missing user_id or order_items")

        new_order = Order(user_id=user_id, status="Pending")
        db.session.add(new_order)
        db.session.commit()

        for item in order_items:
            menuitem_id = item.get('menuitem_id')
            quantity = item.get('quantity')
            if not menuitem_id or quantity is None:
                raise ValueError("Missing menuitem_id or quantity")
            menu_item = MenuItem.query.get(menuitem_id)
            if not menu_item:
                raise ValueError(f"Menu item with ID {menuitem_id} not found")
            order_item = OrderItem(
                order_id=new_order.id, 
                menu_item_id=menuitem_id, 
                quantity=quantity,
                menuitem_name=menu_item.name, 
                menuitem_price=menu_item.price, 
                menu_item_image=menu_item.image
            )
            db.session.add(order_item)

        db.session.commit()
        return jsonify(new_order.to_dict(include_order_items=True)), 201

    except ValueError as e:
        app.logger.error(f"ValueError: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Error creating order: {e}")
        return jsonify({"error": "Failed to create order"}), 500

@app.route('/api/orders/<int:id>', methods=['PUT'])
def update_order(id):
    try:
        data = request.get_json()
        order = Order.query.get(id)
        if not order:
            raise NotFound("Order not found")

        order.status = data.get('status', order.status)
        db.session.commit()
        return jsonify(order.to_dict()), 200

    except NotFound as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        app.logger.error(f"Error updating order: {e}")
        return jsonify({"error": "Failed to update order"}), 500

@app.route('/api/orders/<int:id>', methods=['DELETE'])
def delete_order(id):
    try:
        order = Order.query.get(id)
        if not order:
            raise NotFound("Order not found")

        db.session.delete(order)
        db.session.commit()
        return jsonify({"message": "Order deleted successfully"}), 200

    except NotFound as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        app.logger.error(f"Error deleting order: {e}")
        return jsonify({"error": "Failed to delete order"}), 500

if __name__ == '__main__':
    app.run(port=5555, debug=True)
