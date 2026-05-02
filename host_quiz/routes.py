from flask import Flask,Blueprint,render_template,session,request,url_for
from database import db
from shared_state import rooms,live_games
from extensions import socketio
from flask_socketio import SocketIO,join_room,leave_room,send
from models.questions import Question
from models.options import Option
from models.quizzes import Quiz
from models.quiz_sessions import QuizSession
import requests
from datetime import datetime,timedelta
from string import ascii_uppercase
import random
from flask_login import login_required

host_bp = Blueprint('host',__name__,url_prefix='/host')

def generate_room_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        if code not in rooms:
            break
    return code


@host_bp.route('/host',methods=['GET','POST'])
@login_required
def host():
    if request.method == 'POST':
        quiz_id = request.form.get('quizes')
        session['quiz_id'] = quiz_id

        room = generate_room_code(4)
        new_session = QuizSession(
            quiz_id=int(quiz_id),
            host_id=session.get('id'),
            room_code=room,
            status='waiting'
        )
        db.session.add(new_session)
        db.session.commit()
        session['session_id'] = new_session.id
        rooms[room] = {"members" : 0, "messages":[],"name":[]}
        session['room'] = room
        session['name'] = "Host" 

        return render_template('host_lobby.html',quiz_id=quiz_id,code=room)
    quizes = Quiz.query.filter_by(created_by=session.get('id')).all()
    return render_template('host_select_quiz.html',quizes=quizes)



if __name__ == '__main__':
    host_bp.run(debug=True)