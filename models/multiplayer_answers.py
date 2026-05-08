from database import db
from datetime import datetime


class MultiplayerAnswer(db.Model):
    __tablename__ = 'multiplayer_answers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey('quiz_sessions.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False,index=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL', onupdate='CASCADE'),
        nullable=True,index=True
    )
    player_name = db.Column(db.String(100), nullable=False)
    question_id = db.Column(
        db.Integer,
        db.ForeignKey('questions.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False
    )
    selected_option_id = db.Column(
        db.Integer,
        db.ForeignKey('options.id', ondelete='SET NULL', onupdate='CASCADE'),
        nullable=True
    )
    is_correct = db.Column(db.Boolean, default=False)
    points_earned = db.Column(db.Integer, default=0)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    session = db.relationship('QuizSession', backref=db.backref('answers', cascade='all, delete'))
    user = db.relationship('User', backref=db.backref('multiplayer_answers', cascade='all, delete'))
    question = db.relationship('Question', backref=db.backref('multiplayer_answers', cascade='all, delete'))
    selected_option = db.relationship('Option', backref=db.backref('chosen_by', cascade='all, delete'))
