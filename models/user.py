from database import db
from datetime import datetime
from flask_login import UserMixin

class User(UserMixin,db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False,index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    login_type = db.Column( db.Enum('normal', 'google', name='login_type_enum'), nullable=False)
    role = db.Column(db.Enum('admin', 'user', name='role_enum'), nullable=False, default='user')
    created_at = db.Column( db.DateTime, default=datetime.utcnow)