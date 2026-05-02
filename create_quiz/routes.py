from flask import Flask,Blueprint,render_template,session,request,url_for,jsonify,redirect
from database import db
from models.questions import Question
from models.options import Option
from models.quizzes import Quiz
import requests
from datetime import datetime,timedelta
from string import ascii_uppercase
import random
from flask_login import login_required
create_bp = Blueprint('create',__name__,url_prefix='/create')


@create_bp.route('/', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        title = request.form.get('title')

        new_quiz = Quiz(
            title=title,
            created_by= session.get('id')
        )

        db.session.add(new_quiz)
        db.session.commit()

        session['quiz_id'] = new_quiz.id

        return redirect(url_for('create.add'))

    return render_template('create.html')


@create_bp.route('/add', methods=['GET'])
@login_required
def add():
    if 'quiz_id' not in session:
        return redirect(url_for('create.create'))
    return render_template('addquestions.html')


@create_bp.route('/addquestion', methods=['POST'])
@login_required
def addquestion():
    data = request.get_json()

    quiz_id = session.get('quiz_id')

    if not quiz_id:
        return jsonify({"error": "Quiz not found"}), 400

    question = Question(
        quiz_id=quiz_id,
        question_text=data['question'],
        category=None,
        points=int(data['points']),
        is_bonus=data['is_bonus']
    )

    db.session.add(question)
    db.session.commit()

    option_count = data.get('option_count', 4)

    if option_count == 2:
        options_data = [
            ("A", data['option1']),
            ("B", data['option2']),
        ]
    else:
        options_data = [
            ("A", data['option1']),
            ("B", data['option2']),
            ("C", data.get('option3', '')),
            ("D", data.get('option4', '')),
        ]

    for key, text in options_data:
        option = Option(
            question_id=question.id,
            option_text=text,
            is_correct=True if data['correct'] == key else False
        )
        db.session.add(option)

    db.session.commit()

    return jsonify({
        "message": "Question added successfully !"
    })


if __name__ == '__main__':
    create_bp.run(debug=True)
