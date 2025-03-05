from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend interaction

# Database Configuration (Change as needed)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school_management.db'  # Use SQLite (or update for PostgreSQL/MySQL)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Database & Migration
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)  # Should be hashed in production
    role = db.Column(db.String(50), nullable=False, default="User")

    __table_args__ = (
        db.UniqueConstraint('email', name='uq_user_email'),  # ✅ Ensuring named constraints
    )

# Student Model
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)

@app.route('/version', methods=['GET'])
def version():
    return jsonify({"version": "1.0.0", "status": "Running"})
# Test API Route
@app.route('/')
def home():
    return jsonify({"message": "Welcome to the School Management API!"})

# Register User API
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Email and password are required'}), 400

    new_user = User(
        first_name=data.get('first_name', 'Unknown'),
        last_name=data.get('last_name', 'Unknown'),
        email=data['email'],
        password=data['password'],  # Hash before storing
        role=data.get('role', 'User')
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201

# Get Students API
@app.route('/students', methods=['GET'])
def get_students():
    students = Student.query.all()
    return jsonify([{'id': s.id, 'name': f"{s.first_name} {s.last_name}", 'email': s.email} for s in students])

# Run the Flask App
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
