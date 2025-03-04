from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import os
from functools import wraps
import pandas as pd

app = Flask(__name__)
CORS(app)

# ✅ Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "your_secret_key")

db = SQLAlchemy(app)

# ✅ User Model (Includes Role)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('Admin', 'Teacher', 'Staff', 'Student'), nullable=False)

# ✅ Student Model
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.Enum('Male', 'Female', 'Other'), nullable=False)
    grade = db.Column(db.String(10), nullable=False)
    fee = db.Column(db.Float, nullable=False)

# ✅ Finance Model (Income & Expenses)
class Finance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.Enum('Income', 'Expense'), nullable=False)

# ✅ Authentication Middleware
def token_required(role_required):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.headers.get('x-access-token')
            if not token:
                return jsonify({'message': 'Token is missing!'}), 403
            try:
                data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                current_user = User.query.filter_by(id=data['user_id']).first()
                if not current_user or current_user.role != role_required:
                    return jsonify({'message': 'Unauthorized access!'}), 403
            except:
                return jsonify({'message': 'Invalid token!'}), 403
            return f(current_user, *args, **kwargs)
        return decorated_function
    return decorator

# ✅ User Registration
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    hashed_password = generate_password_hash(data['password'], method='sha256')
    new_user = User(username=data['username'], password_hash=hashed_password, role=data['role'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully!'})

# ✅ User Login
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password_hash, data['password']):
        token = jwt.encode({'user_id': user.id, 'role': user.role, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)}, 
                           app.config['SECRET_KEY'], algorithm='HS256')
        return jsonify({'token': token, 'role': user.role})
    return jsonify({'message': 'Invalid credentials!'}), 401

# ✅ Dashboard API: Student Statistics
@app.route('/dashboard/students', methods=['GET'])
def student_dashboard():
    total_students = Student.query.count()
    male_students = Student.query.filter_by(gender='Male').count()
    female_students = Student.query.filter_by(gender='Female').count()
    return jsonify({
        'total_students': total_students,
        'male_students': male_students,
        'female_students': female_students
    })

# ✅ Dashboard API: Finance Statistics
@app.route('/dashboard/finance', methods=['GET'])
def finance_dashboard():
    total_income = db.session.query(db.func.sum(Finance.amount)).filter(Finance.type == 'Income').scalar() or 0
    total_expense = db.session.query(db.func.sum(Finance.amount)).filter(Finance.type == 'Expense').scalar() or 0
    return jsonify({
        'total_income': total_income,
        'total_expense': total_expense
    })

# ✅ Export Student Data as CSV
@app.route('/export/students', methods=['GET'])
def export_students():
    students = Student.query.all()
    data = [{'Name': s.first_name + " " + s.last_name, 'Gender': s.gender, 'Grade': s.grade, 'Fee': s.fee} for s in students]
    df = pd.DataFrame(data)
    file_path = "students_export.csv"
    df.to_csv(file_path, index=False)
    return jsonify({'message': 'File ready for download', 'file': file_path})

# ✅ Initialize Database Without `before_first_request`
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
