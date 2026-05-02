from flask import Flask,Blueprint,render_template,session,request,url_for
from database import db
from flask_socketio import SocketIO,join_room,leave_room,send
from models.questions import Question
from models.options import Option
from models.quizzes import Quiz
from shared_state import live_games,rooms
from flask_socketio import join_room,leave_room
import requests
import host_quiz.socket_events
from datetime import datetime,timedelta
from string import ascii_uppercase
import random
from shared_state import rooms
from flask_login import login_required



join_bp = Blueprint('join',__name__,url_prefix='/join')



@join_bp.route('/',methods=['GET','POST'])
@login_required
def join():
    if request.method == 'POST':
        code = request.form.get('code')
        name = request.form.get('name')
        
        if code not in rooms:
            return render_template('join.html',error='enter a valid Room code please!',code=code,name=name)
        
        session['room'] = code
        session['name'] = name 
        return render_template('player_lobby.html')

    return render_template('join.html')



if __name__ == '__main__':
    join_bp.run(debug=True)