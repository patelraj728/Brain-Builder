from flask import Blueprint,render_template,redirect,session,request,url_for,flash
from database import db
from models.user import User
from models.results import Results
from models.quizzes import Quiz
from models.questions import Question
from models.options import Option
from models.multiplayer_answers import MultiplayerAnswer
from models.quiz_sessions import QuizSession
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash,check_password_hash
import requests
import os
import random
import smtplib
import time
from flask_login import login_required,logout_user,login_user

user_bp = Blueprint('login',__name__,url_prefix='/login')

    
GOOGLE_CLIENT_ID = os.environ['GOOGLE_CLIENT_ID']
GOOGLE_CLIENT_SECRET = os.environ['GOOGLE_CLIENT_SECRET']

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

EMAIL = os.environ["EMAIL_USER"]
PASSWORD = os.environ["EMAIL_PASS"] # from Google



@user_bp.route('/create_user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        email = request.form.get('email')

        # Only check if user already exists
        if User.query.filter_by(email=email).first():
            return render_template('createuser.html', error="You already have an account")
        # DO NOT create user here anymore
        # Let JS handle OTP flow
        return render_template('createuser.html')

    return render_template('createuser.html')


@user_bp.route('/signup-send-otp', methods=['POST'])
def signup_send_otp():
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')

    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return {"status": "error", "message": "Email already registered"}
    if len(password) < 8:
        return {
        "status": "error",
        "message": "Password must be at least 8 characters"
        }
    otp = str(random.randint(100000, 999999))

    session['signup_otp'] = otp
    session['signup_expiry'] = time.time() + 300
    session['signup_email'] = email
    session['signup_name'] = name
    session['signup_password'] = password

    # Send email
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(EMAIL, PASSWORD)

    message = f"Subject: Email Verification\n\nYour OTP is {otp}"
    server.sendmail(EMAIL, email, message)
    server.quit()

    print("Signup OTP:", otp)

    return {"status": "success"}


@user_bp.route('/signup-verify-otp', methods=['POST'])
def signup_verify_otp():
    user_otp = request.form.get('otp')
    attempts = session.get('otp_attempts', 0)

    if attempts >= 5:
        return {
        "status": "error",
        "message": "Too many attempts"
        }

    session['otp_attempts'] = attempts + 1
    
    if time.time() > session.get('signup_expiry', 0):
        return {"status": "error", "message": "OTP expired"}

    if user_otp != session.get('signup_otp'):
        return {"status": "error", "message": "Invalid OTP"}

    # Create user ONLY after OTP success
    new_user = User(
        name=session.get('signup_name'),
        email=session.get('signup_email'),
        password_hash=generate_password_hash(session.get('signup_password')),
        login_type='normal'
    )

    db.session.add(new_user)
    db.session.commit()

    # Clear session
    session.pop('signup_otp', None)
    session.pop('signup_expiry', None)

    return {"status": "success"}


@user_bp.route('/home', methods=['GET','POST'])
@login_required
def home():
    return render_template('home.html')



@user_bp.route('/google')
def google_login():
    redirect_uri = "https://brain-builder.onrender.com/login/google/callback"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    url = GOOGLE_AUTH_URL + "?" + "&".join(
        [f"{k}={v}" for k, v in params.items()]
    )
    return redirect(url)


@user_bp.route('/google/callback')
def google_callback():
    code = request.args.get('code')
    if not code:
        return "Authorization failed", 400

    # Exchange code for access token
    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": url_for("login.google_callback", _external=True,_scheme='https'),
        "grant_type": "authorization_code"
    }

    token_response = requests.post(GOOGLE_TOKEN_URL, data=token_data,timeout=10)
    token_json = token_response.json()

    access_token = token_json.get("access_token")
    if not access_token:
        return "Failed to get access token", 400

    # Get user info from Google
    userinfo_response = requests.get(
        GOOGLE_USERINFO_URL,
        params={"access_token": access_token}
    )

    userinfo = userinfo_response.json()

    email = userinfo.get("email")
    name = userinfo.get("name")

    if not email:
        return "Google login failed", 400

    # Check if user already exists
    user = User.query.filter_by(email=email).first()

    if not user:
        user = User(
            name=name,
            email=email,
            login_type='google',
            password_hash=None,   # No password for Google users
            role='user'
        )
        db.session.add(user)
        db.session.commit()

    # Login user
    login_user(user)

    session['email'] = email
    session['id'] = user.id
    session['role'] = user.role
    session['logged_in'] = True

    return redirect(url_for('login.home'))



@user_bp.route('/profile')
@login_required
def profile():
    data = Results.query.filter_by(user_id=session.get('id')).all()
    quizes = Quiz.query.filter_by(created_by=session.get('id')).all()
    return render_template('profile.html',data=data,quizes=quizes)

@user_bp.route('/about')
@login_required
def about():
    return render_template('about.html')

@user_bp.route('/profile/session/<int:session_id>')
@login_required
def profile_session_detail(session_id):
    user_id = session.get('id')
    if not user_id:
        return redirect(url_for('login'))
    qs = QuizSession.query.get_or_404(session_id)
    result = Results.query.filter_by(session_id=session_id, user_id=user_id).first()
    answers = MultiplayerAnswer.query.filter_by(session_id=session_id, user_id=user_id).order_by(MultiplayerAnswer.answered_at).all()
    all_results = Results.query.filter_by(session_id=session_id).order_by(Results.total_score.desc()).all()
    return render_template('profile_session_detail.html', qs=qs, result=result, answers=answers, all_results=all_results)


@user_bp.route('/profile/quiz/<int:quiz_id>')
@login_required
def view_quiz(quiz_id):
    user_id = session.get('id')
    if not user_id:
        return redirect(url_for('login'))
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.created_by != user_id:
        return redirect(url_for('login.profile'))
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.question_order).all()
    return render_template('view_quiz.html', quiz=quiz, questions=questions)


@user_bp.route('/profile/quiz/<int:quiz_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_quiz(quiz_id):
    user_id = session.get('id')
    if not user_id:
        return redirect(url_for('login'))
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.created_by != user_id:
        return redirect(url_for('login.profile'))
    
    if request.method == 'POST':
        quiz.title = request.form.get('title', quiz.title)
        db.session.commit()
        return redirect(url_for('login.view_quiz', quiz_id=quiz_id))
    
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.question_order).all()
    return render_template('edit_quiz.html', quiz=quiz, questions=questions)


@user_bp.route('/profile/quiz/<int:quiz_id>/question/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_question(quiz_id, question_id):
    user_id = session.get('id')
    if not user_id:
        return redirect(url_for('login'))
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.created_by != user_id:
        return redirect(url_for('login.profile'))
    question = Question.query.get_or_404(question_id)
    
    if request.method == 'POST':
        question.question_text = request.form.get('question_text')
        question.points = int(request.form.get('points', 10))
        question.is_bonus = bool(request.form.get('is_bonus'))
        
        option_ids = request.form.getlist('option_id')
        option_texts = request.form.getlist('option_text')
        correct_index = int(request.form.get('correct_option', 0))
        
        for i, opt_id in enumerate(option_ids):
            opt = Option.query.get(int(opt_id))
            if opt and i < len(option_texts):
                opt.option_text = option_texts[i].strip()
                opt.is_correct = (i == correct_index)
        
        db.session.commit()
        return redirect(url_for('login.edit_quiz', quiz_id=quiz_id))
    
    return render_template('edit_question.html', quiz=quiz, question=question)


@user_bp.route('/profile/quiz/<int:quiz_id>/question/<int:question_id>/delete', methods=['POST'])
@login_required
def delete_question(quiz_id, question_id):
    user_id = session.get('id')
    if not user_id:
        return redirect(url_for('login'))
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.created_by != user_id:
        return redirect(url_for('login.profile'))
    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    return redirect(url_for('login.edit_quiz', quiz_id=quiz_id))



# Verify page
@user_bp.route('/verify-email',methods=['GET'])
def verify_email_page():
    show_otp = request.args.get('show_otp')
    email = request.args.get('email')
    return render_template('verify.html', show_otp=show_otp, email=email)


@user_bp.route('/send-email-otp', methods=['POST'])
def send_email_otp():
    resend = request.form.get('resend',False)
    if resend != False:
        user_email = session.get('email')
    else:
        user_email = request.form.get('email')
    
    users = User.query.filter_by(email=user_email).first()
    if users:
        otp = str(random.randint(100000, 999999))
        session['otp'] = otp
        session['expiry'] = time.time() + 120
        session['email'] = user_email
        session['name'] = request.form.get('name')
        # Send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL, PASSWORD)

        message = f"Subject: Email Verification\n\nYour OTP is {otp}"

        server.sendmail(EMAIL, user_email, message.encode('utf-8'))
        server.quit()

        print("OTP:", otp)

        return redirect(url_for('login.verify_email_page', show_otp=1, email=user_email))
    else:
        return redirect('/login/verify-email?error=User%20Does%20not%20Exist')

# Verify OTP
@user_bp.route('/verify-email-otp', methods=['POST'])
def verify_email_otp():
    user_otp = request.form.get('otp')

    if time.time() > session.get('expiry', 0):
        flash("OTP expired. Please request a new one.", "error")
        return redirect(url_for('login.verify_email_otp'))

    if user_otp == session.get('otp'):
        return redirect(url_for('login.newpassword'))
    else:
        flash("Invalid OTP. Please try again.", "error")
        return redirect(url_for('login.verify_email_page', show_otp=1, email=session.get('email'),otp=user_otp))
    
@user_bp.route('/newpassword',methods=['GET','POST'])
def newpassword():
    if request.method == 'POST':
        email = session.get('email')
        new_password = request.form.get('password')

        User.query.filter_by(email=email).update({
        User.password_hash: generate_password_hash(new_password)
        })
        db.session.commit()

        return redirect(url_for('login'))
    return render_template('newpassword.html')

@user_bp.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('login'))