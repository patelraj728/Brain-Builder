from database import db
from datetime import datetime
from models.quiz_sessions import QuizSession


class Results(db.Model):
    __tablename__ = 'results'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('quiz_sessions.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=True)
    total_score = db.Column(db.Integer, nullable=False)
    played_at = db.Column(db.DateTime, default=datetime.utcnow)

    quiz = db.relationship('Quiz', backref=db.backref('results', cascade='all, delete'))
    user = db.relationship('User', backref=db.backref('results', cascade='all, delete'))
    session = db.relationship('QuizSession', backref=db.backref('results', cascade='all, delete'))