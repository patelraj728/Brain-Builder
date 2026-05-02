from database import db
from sqlalchemy import Enum


class QuizSession(db.Model):
    __tablename__ = 'quiz_sessions'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    quiz_id = db.Column(db.Integer,db.ForeignKey('quizzes.id', ondelete='CASCADE', onupdate='CASCADE'),nullable=False)
    host_id = db.Column(db.Integer,db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),nullable=False)
    room_code = db.Column(db.String(10), unique=True, nullable=False)
    status = db.Column(Enum('waiting', 'started', 'ended', name='session_status'),nullable=False,default='waiting')
    started_at = db.Column(db.DateTime, nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    # Relationships
    quiz = db.relationship('Quiz', backref=db.backref('sessions', cascade='all, delete'))
    host = db.relationship('User', backref=db.backref('hosted_sessions', cascade='all, delete'))
