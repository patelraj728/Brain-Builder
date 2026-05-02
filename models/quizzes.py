from database import db
from datetime import datetime
from models.user import User

class Quiz(db.Model):
    __tablename__ = 'quizzes'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    created_by = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', backref=db.backref('quizzes', cascade='all, delete'))
