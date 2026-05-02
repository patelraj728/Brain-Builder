from flask import Flask,render_template,session,redirect,url_for,Blueprint,request,jsonify
from database import db
from models.user import User
from models.quizzes import Quiz
from models.questions import Question
from models.options import Option
from sqlalchemy.sql.expression import func
from models.results import Results
from datetime import datetime,timedelta

solo_bp = Blueprint('solo',__name__,url_prefix='/solo')


# for setup page
@solo_bp.route('/setup',methods=['GET','POST'])
def setup():
    if request.method == 'POST':
        session['category'] = request.form.get('category')
        session['numberofQue'] = request.form.get('num')
        return redirect(url_for('solo.quiz'))

    category_list = db.session.query(Question.category).distinct().all()
    categories = [item[0] for item in category_list]
    return render_template('setup.html', categories=categories)


# for dynamic questions 
@solo_bp.route('/get_num_questions')
def get_num_questions():
    category = request.args.get('category')
    count = db.session.query(Question).filter_by(category=category).count()
    return jsonify({'count': count})



#for result page
@solo_bp.route('/result',methods=['GET','POST'])
def result():   
    if request.method == 'POST':
        data = request.get_json()
        session['totalscore'] = data.get("totalscore", 0)
        result = Results(
                        quiz_id = 1,
                        user_id = session.get('id'),
                        session_id = None,
                        total_score = session.get('totalscore')
                        )
        db.session.add(result)
        db.session.commit()
    return render_template('result.html',score=session.get('totalscore'))



#for quiz page
@solo_bp.route('/quiz',methods=['GET','POST'])
def quiz():   
    totalquestions = session.get('numberofQue')
    return render_template('quiz.html',totalquestions=totalquestions)


#for get questions from backend 

@solo_bp.route('/get_question',methods=['POST'])
def get_question():
    
    data = request.get_json()
    index = data.get('index' , 0)

    if int(session.get('numberofQue')) > index:
        answered = session.get('answered_questions', [])
        questions = (
            Question.query
            .filter_by(quiz_id=1, category=session.get('category'))
            .filter(~Question.id.in_(answered))
            .order_by(func.rand())
            .first()
        )
        if not questions:
            return jsonify({
                "success": False,
                "text": None,
                "option_texts" : None
            })
        
        answered.append(questions.id)
        session['answered_questions'] = answered

        questionsBonus = questions.is_bonus
        question_end_time = datetime.utcnow() + timedelta(seconds=30)
        session['question_end_time'] = question_end_time.timestamp()

        option_texts = [opt.option_text for opt in questions.options]
        option_ids = [opt.id for opt in questions.options]

        return jsonify({
            "success": True,
            "text": questions.question_text,
            "option_texts" : option_texts,
            "option_ids":option_ids,
            "time_limit": 30,
            "questionsBonus":questionsBonus
        })
    return jsonify({
        "success": False,
        "text": None,
        "option_texts": None
    })





# for check answer and score
@solo_bp.route("/check_answer", methods=['POST'])
def check_answer():

    # 🔥 TIMER VALIDATION
    if datetime.utcnow().timestamp() > session.get('question_end_time', 0):
        return jsonify({
            "success": False,
            "msg": "Time Over!",
            "score": request.json.get('current_score', 0)
        })

    data = request.get_json()
    selected_id = data.get('selected_id')
    current_score = data.get('current_score', 0)

    options = Option.query.filter_by(id=selected_id).first()

    question_id = options.question_id

    question_points = db.session.query(Question.points)\
                                 .filter(Question.id == question_id)\
                                 .scalar()

    is_bonus = db.session.query(Question.is_bonus)\
                         .filter(Question.id == question_id)\
                         .scalar()

    if options.is_correct:
        if is_bonus:
            current_score += (question_points * 2)
        else:
            current_score += question_points
        msg = "Correct ✅"
    else:
        msg = "Incorrect ❌"

    return jsonify({
        "success": True,
        "msg": msg,
        "score": current_score
    })



if __name__ == '__main__':
    solo_bp.run(debug=True)