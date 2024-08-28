from flask import Flask, request, jsonify
from functools import wraps 
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from dotenv import load_dotenv
from utils.calculate_result import calculate_result
import os
import jwt

load_dotenv()

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 15
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 7 

client = MongoClient(os.getenv('MONGO_URI'))
db = client.quiz_db

def create_access_token(user_id):
    return jwt.encode({
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(minutes=app.config['JWT_ACCESS_TOKEN_EXPIRES'])
    }, app.config['JWT_SECRET_KEY'], algorithm='HS256')

def create_refresh_token(user_id):
    return jwt.encode({
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=app.config['JWT_REFRESH_TOKEN_EXPIRES'])
    }, app.config['JWT_SECRET_KEY'], algorithm='HS256')

def decode_token(token):
    try:
        return jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 403
        token = token.split(" ")[1]
        decoded_token = decode_token(token)
        if not decoded_token:
            return jsonify({'message': 'Token is invalid or expired!'}), 403
        request.user_id = decoded_token['user_id']
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = db.users.find_one({'email': data['email']})
    if user and check_password_hash(user['password'], data['password']):
        access_token = create_access_token(str(user['_id']))
        refresh_token = create_refresh_token(str(user['_id']))
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/refresh', methods=['POST'])
def refresh_token():
    refresh_token = request.json.get('refresh_token')
    decoded_token = decode_token(refresh_token)
    if not decoded_token:
        return jsonify({'message': 'Refresh token is invalid or expired!'}), 403
    
    new_access_token = create_access_token(decoded_token['user_id'])
    return jsonify({'access_token': new_access_token}), 200

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

#Route: Get Test List
@app.route('/tests', methods=['GET'])
def get_tests():
    per_page = int(request.args.get('per_page', 10))
    last_id = request.args.get('last_id')
    
    query = {}
    if last_id:
        query['_id'] = {'$gt': ObjectId(last_id)}
    
    tests_cursor = db.tests.find(query).sort('_id', 1).limit(per_page)
    tests = list(tests_cursor)
    
    for test in tests:
        test['_id'] = str(test['_id'])
    
    next_id = tests[-1]['_id'] if tests else None
    
    response = {
        'tests': tests,
        'per_page': per_page,
        'next_id': next_id
    }
    
    return jsonify(response)

#Route: Get Test Specifics
@app.route('/tests/<test_id>', methods=['GET'])
def get_test(test_id):
    test = db.tests.find_one({'_id': ObjectId(test_id)})
    if test:
        test['_id'] = str(test['_id'])
        return jsonify(test)
    return jsonify(message="Test not found"), 404

# Route: Submit Test
@app.route('/tests/submit', methods=['POST'])
@token_required
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
@token_required
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
@token_required
def logout():
    refresh_token = request.json.get('refresh_token')
    return jsonify({'message': 'Logged out successfully'}), 200

if __name__ == '__main__':
    app.run(debug=True)
