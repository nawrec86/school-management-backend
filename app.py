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

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum('Present', 'Absent', 'Late'), nullable=False)
    student = db.relationship('Student', backref=db.backref('attendance', lazy=True))

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.Enum('Paid', 'Pending'), nullable=False)
    student = db.relationship('Student', backref=db.backref('payments', lazy=True))


# ✅ Authentication Middleware


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

from functools import wraps
import jwt
from flask import request, jsonify

def token_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.headers.get('x-access-token')
            if not token:
                return jsonify({'message': 'Token is missing!'}), 403
            try:
                data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
                current_user = User.query.filter_by(id=data['user_id']).first()
                if not current_user or current_user.role not in allowed_roles:
                    return jsonify({'message': 'Unauthorized access!'}), 403
            except:
                return jsonify({'message': 'Invalid token!'}), 403
            return f(current_user, *args, **kwargs)
        return decorated_function
    return decorator

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

from datetime import datetime

# ✅ Mark Attendance for a Student
@app.route('/attendance', methods=['POST'])
@token_required(['Admin', 'Teacher'])
def mark_attendance(current_user):
    data = request.json
    student = Student.query.get(data['student_id'])
    if not student:
        return jsonify({'message': 'Student not found'}), 404

    new_attendance = Attendance(
        student_id=student.id,
        date=datetime.strptime(data['date'], "%Y-%m-%d"),
        status=data['status']
    )
    db.session.add(new_attendance)
    db.session.commit()

    return jsonify({'message': 'Attendance recorded successfully'})

# ✅ Get Attendance Records
@app.route('/attendance/<int:student_id>', methods=['GET'])
@token_required(['Admin', 'Teacher'])
def get_attendance(current_user, student_id):
    attendance_records = Attendance.query.filter_by(student_id=student_id).all()
    records = [{'date': a.date.strftime("%Y-%m-%d"), 'status': a.status} for a in attendance_records]
    return jsonify(records)

# ✅ Make a Payment for a Student
@app.route('/payment', methods=['POST'])
@token_required(['Admin', 'Staff'])
def make_payment(current_user):
    data = request.json
    student = Student.query.get(data['student_id'])
    if not student:
        return jsonify({'message': 'Student not found'}), 404

    new_payment = Payment(
        student_id=student.id,
        date=datetime.strptime(data['date'], "%Y-%m-%d"),
        amount=data['amount'],
        status=data['status']
    )
    db.session.add(new_payment)
    db.session.commit()

    return jsonify({'message': 'Payment recorded successfully'})

# ✅ Get Payment History
@app.route('/payments/<int:student_id>', methods=['GET'])
@token_required(['Admin', 'Staff'])
def get_payments(current_user, student_id):
    payments = Payment.query.filter_by(student_id=student_id).all()
    records = [{'date': p.date.strftime("%Y-%m-%d"), 'amount': p.amount, 'status': p.status} for p in payments]
    return jsonify(records)



# ✅ Export Student Data as CSV
@app.route('/export/students', methods=['GET'])
def export_students():
    students = Student.query.all()
    data = [{'Name': s.first_name + " " + s.last_name, 'Gender': s.gender, 'Grade': s.grade, 'Fee': s.fee} for s in students]
    df = pd.DataFrame(data)
    file_path = "students_export.csv"
    df.to_csv(file_path, index=False)
    return jsonify({'message': 'File ready for download', 'file': file_path})
    @app.route('/admin-only', methods=['GET'])
@token_required(['Admin'])
def admin_only(current_user):
    return jsonify({'message': 'Welcome, Admin! This is a protected route.'})

@app.route('/teacher-dashboard', methods=['GET'])
@token_required(['Admin', 'Teacher'])
def teacher_dashboard(current_user):
    return jsonify({'message': 'Welcome, Teacher! You have access to this data.'})

@app.route('/staff-panel', methods=['GET'])
@token_required(['Admin', 'Staff'])
def staff_panel(current_user):
    return jsonify({'message': 'Welcome, Staff! You can manage attendance.'})


# ✅ Initialize Database Without `before_first_request`
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
