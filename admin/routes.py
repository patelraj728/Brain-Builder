from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify, flash
from database import db
from models.user import User
from models.quizzes import Quiz
from models.questions import Question
from models.options import Option
from models.quiz_sessions import QuizSession
from models.results import Results
from models.multiplayer_answers import MultiplayerAnswer
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('id'):
            return redirect(url_for('login'))
        user = User.query.get(session['id'])
        if not user or user.role != 'admin':
            return redirect(url_for('login.home'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@admin_required
def dashboard():
    total_users = User.query.count()
    total_quizzes = Quiz.query.count()
    total_questions = Question.query.count()
    total_sessions = QuizSession.query.count()
    active_sessions = QuizSession.query.filter_by(status='started').count()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_sessions = QuizSession.query.order_by(QuizSession.started_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_quizzes=total_quizzes,
                           total_questions=total_questions,
                           total_sessions=total_sessions,
                           active_sessions=active_sessions,
                           recent_users=recent_users,
                           recent_sessions=recent_sessions)


# ──────────────────── USERS ────────────────────

@admin_bp.route('/users')
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == session.get('id'):
        return jsonify({'error': 'Cannot delete yourself'}), 400
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/toggle_role', methods=['POST'])
@admin_required
def toggle_role(user_id):
    user = User.query.get_or_404(user_id)
    user.role = 'user' if user.role == 'admin' else 'admin'
    db.session.commit()
    return redirect(url_for('admin.users'))


# ──────────────────── QUIZ QUESTIONS (quiz_id=1) ────────────────────

@admin_bp.route('/quiz/<int:quiz_id>/questions')
@admin_required
def quiz_questions(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.question_order).all()
    return render_template('admin/questions.html', quiz=quiz, questions=questions)


@admin_bp.route('/quiz/<int:quiz_id>/questions/add', methods=['GET', 'POST'])
@admin_required
def add_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        q = Question(
            quiz_id=quiz_id,
            question_text=request.form.get('question_text'),
            category=request.form.get('category'),
            points=int(request.form.get('points', 10)),
            is_bonus=bool(request.form.get('is_bonus')),
            question_order=int(request.form.get('question_order', 0))
        )
        db.session.add(q)
        db.session.flush()

        option_texts = request.form.getlist('option_text')
        correct_index = int(request.form.get('correct_option', 0))
        for i, text in enumerate(option_texts):
            if text.strip():
                opt = Option(question_id=q.id, option_text=text.strip(), is_correct=(i == correct_index))
                db.session.add(opt)
        db.session.commit()
        return redirect(url_for('admin.quiz_questions', quiz_id=quiz_id))
    return render_template('admin/question_form.html', quiz=quiz, question=None)


@admin_bp.route('/question/<int:question_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz = question.quiz
    if request.method == 'POST':
        question.question_text = request.form.get('question_text')
        question.category = request.form.get('category')
        question.points = int(request.form.get('points', 10))
        question.is_bonus = bool(request.form.get('is_bonus'))
        question.question_order = int(request.form.get('question_order', 0))

        # Update options
        option_ids = request.form.getlist('option_id')
        option_texts = request.form.getlist('option_text')
        correct_index = int(request.form.get('correct_option', 0))

        for i, opt_id in enumerate(option_ids):
            opt = Option.query.get(int(opt_id))
            if opt and i < len(option_texts):
                opt.option_text = option_texts[i].strip()
                opt.is_correct = (i == correct_index)

        db.session.commit()
        return redirect(url_for('admin.quiz_questions', quiz_id=quiz.id))
    return render_template('admin/question_form.html', quiz=quiz, question=question)


@admin_bp.route('/question/<int:question_id>/delete', methods=['POST'])
@admin_required
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz_id = question.quiz_id
    db.session.delete(question)
    db.session.commit()
    return redirect(url_for('admin.quiz_questions', quiz_id=quiz_id))


# ──────────────────── MULTIPLAYER SESSIONS ────────────────────

@admin_bp.route('/sessions')
@admin_required
def sessions():
    all_sessions = QuizSession.query.order_by(QuizSession.started_at.desc()).all()
    return render_template('admin/sessions.html', sessions=all_sessions)


@admin_bp.route('/sessions/<int:session_id>')
@admin_required
def session_detail(session_id):
    qs = QuizSession.query.get_or_404(session_id)
    results = Results.query.filter_by(session_id=session_id).order_by(Results.total_score.desc()).all()
    answers = MultiplayerAnswer.query.filter_by(session_id=session_id).order_by(MultiplayerAnswer.answered_at).all()
    return render_template('admin/session_detail.html', session=qs, results=results, answers=answers)
