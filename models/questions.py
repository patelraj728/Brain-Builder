from database import db


class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(
        db.Integer,
        db.ForeignKey('quizzes.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False,index=True
    )
    question_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=True)
    points = db.Column(db.Integer, nullable=False)
    is_bonus = db.Column(db.Boolean, default=False)
    question_order = db.Column(db.Integer, nullable=True)

    quiz = db.relationship('Quiz', backref=db.backref(
        'questions',
        cascade='all, delete-orphan',
        order_by='Question.question_order'
    ))
    options = db.relationship('Option', backref='question', cascade='all, delete-orphan')
