from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
from utils.calculate_result import calculate_result 
from datetime import datetime

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
        return jsonify(message="Login successful"), 200
    return jsonify(message="Invalid credentials"), 401

# Route: Get Test List
@app.route('/tests', methods=['GET'])
def get_tests():
    tests = list(db.tests.find())
    for test in tests:
        test['_id'] = str(test['_id'])
    return jsonify(tests)

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
def get_result(submission_id):
   
    submission = db.submissions.find_one({'_id': ObjectId(submission_id)})
    
    if submission:
        
        test = db.tests.find_one({'_id': ObjectId(submission['test_id'])})
        if not test:
            return jsonify(message="Test data not found"), 404

        
        result = calculate_result(test, submission)
        return jsonify(result)
    
    return jsonify(message="Submission not found"), 404

if __name__ == '__main__':
    app.run(debug=True)
