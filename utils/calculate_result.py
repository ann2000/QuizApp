def calculate_result(submission):
    # Logic to calculate results based on submission
    # e.g., compare submitted answers with correct answers
    correct_answers = 0
    total_questions = len(submission['answers'])
    
    for question_id, submitted_answer in submission['answers'].items():
        correct_answer = submission['correct_answers'][question_id]
        if submitted_answer == correct_answer:
            correct_answers += 1
    
    return {
        'score': correct_answers,
        'total': total_questions,
        'percentage': (correct_answers / total_questions) * 100
    }
