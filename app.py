from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
from utils.calculate_result import calculate_result 
from datetime import datetime
import os
import secrets
from functools import wraps

def generate_session_token():
    return secrets.token_hex(32)

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = request.cookies.get('session_token')
        if not session_token:
            return jsonify(message="Unauthorized"), 401
        session = db.sessions.find_one({'session_token': session_token})
        if not session or session['expires_at'] < datetime.utcnow():
            return jsonify(message="Session expired or invalid"), 401
        request.user_id = session['user_id']
        return f(*args, **kwargs)
    return decorated_function


load_dotenv()

app = Flask(__name__)


client = MongoClient(os.getenv('MONGO_URI'))
db = client.quiz_db

# Route: Home
@app.route('/')
def index():
    return "Welcome to the Quiz Application!"

# Route: Signup
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    hashed_password = generate_password_hash(data['password'])
    db.users.insert_one({
        'username': data['username'],
        'email': data['email'],
        'password': hashed_password
    })
    return jsonify(message="User registered successfully"), 201

# Route: Login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = db.users.find_one({'email': data['email']})
    if user and check_password_hash(user['password'], data['password']):
        session_token = generate_session_token()
        db.sessions.insert_one({
            'user_id': str(user['_id']),
            'session_token': session_token,
            'expires_at': datetime.utcnow() + timedelta(hours=1)
        })
        response = jsonify(message="Login successful")
        response.set_cookie('session_token', session_token, httponly=True, secure=True)
        return response, 200
    return jsonify(message="Invalid credentials"), 401


# Route: Get Test List with Pagination
@app.route('/tests', methods=['GET'])
def get_tests():

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))

    skips = per_page * (page - 1)

    tests_cursor = db.tests.find().skip(skips).limit(per_page)
    tests = list(tests_cursor)

    for test in tests:
        test['_id'] = str(test['_id'])

    total_tests = db.tests.count_documents({})

    response = {
        'tests': tests,
        'page': page,
        'per_page': per_page,
        'total_tests': total_tests,
        'total_pages': (total_tests + per_page - 1) // per_page
    }
    
    return jsonify(response)


# Route: Get Test Specifics
@app.route('/tests/<test_id>', methods=['GET'])
def get_test(test_id):
    test = db.tests.find_one({'_id': ObjectId(test_id)})
    if test:
        test['_id'] = str(test['_id'])
        return jsonify(test)
    return jsonify(message="Test not found"), 404

# Route: Submit Test
@app.route('/tests/submit', methods=['POST'])
@require_login
def submit_test():
    data = request.get_json()
    submission_data = {
        "user_id": ObjectId(data['user_id']),
        "test_id": ObjectId(data['test_id']),
        "answers": data['answers'],
        "submitted_at": datetime.utcnow()
    }
    db.submissions.insert_one(submission_data)
    return jsonify(message="Test submitted successfully"), 201

# Route: Get Test Result
@app.route('/tests/result/<submission_id>', methods=['GET'])
@require_login
def get_result(submission_id):
   
    submission = db.submissions.find_one({'_id': ObjectId(submission_id)})
    
    if submission:
        
        test = db.tests.find_one({'_id': ObjectId(submission['test_id'])})
        if not test:
            return jsonify(message="Test data not found"), 404

        
        result = calculate_result(test, submission)
        return jsonify(result)
    
    return jsonify(message="Submission not found"), 404

@app.route('/logout', methods=['POST'])
@require_login
def logout():
    session_token = request.cookies.get('session_token')
    db.sessions.delete_one({'session_token': session_token})
    response = jsonify(message="Logged out successfully")
    response.delete_cookie('session_token') 
    return response, 200

if __name__ == '__main__':
    app.run(debug=True)
