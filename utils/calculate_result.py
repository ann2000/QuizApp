def calculate_result(test, submission):
    correct_answers = 0
    total_questions = sum(len(subject['questions']) for subject in test['subjects'])

    answers_dict = {}
    for subject in submission['answers']:
        for answer in subject['answers']:
            answers_dict[answer['question_id']] = answer['selected_answer']

    # Calculate correct answers
    for subject in test['subjects']:
        for question in subject['questions']:
            question_id = question['question_id']
            user_answer = answers_dict.get(question_id)
            if user_answer == question['correct_answer']:
                correct_answers += 1
    
    result = {
        'score': correct_answers,
        'total': total_questions,
        'percentage': (correct_answers / total_questions) * 100
    }
    return result