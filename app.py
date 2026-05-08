from flask import Flask,render_template,request,redirect,url_for,session,flash
from database import db
from extensions import socketio
from login.routes import user_bp
from solo_quiz.routes import solo_bp
from create_quiz.routes import create_bp
from host_quiz.routes import host_bp
from join_quiz.routes import join_bp
from admin.routes import admin_bp
from models.user import User
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from flask_login import login_user
from models.user import User
import os
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv


load_dotenv()
app = Flask(__name__)
csrf = CSRFProtect(app)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
    'pool_recycle': 1800,
}
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
socketio.init_app(app)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = 'login'

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)
@login_manager.user_loader

def load_user(user_id):
    return User.query.get(int(user_id))

app.register_blueprint(user_bp)
app.register_blueprint(solo_bp)
app.register_blueprint(create_bp)
app.register_blueprint(host_bp)
app.register_blueprint(join_bp)
app.register_blueprint(admin_bp)


app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
# app.run(host="0.0.0.0", port=5000)


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        # user not found
        if not user:
            flash("Invalid credentials", "error")
            return redirect(url_for('login'))

        # google login restriction
        if user.login_type == 'google':
            flash("Please login using Google", "error")
            return redirect(url_for('login'))

        # password check
        if not check_password_hash(user.password_hash, password):
            flash("Invalid password", "error")
            return redirect(url_for('login'))

        # login success
        session['id'] = user.id
        session['email'] = user.email
        session['role'] = user.role
        session['logged_in'] = True
        login_user(user)
        if user.role == 'user':
            return redirect(url_for('login.home'))
        else:
            return redirect(url_for('admin.dashboard'))

    return render_template('login.html')

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404
    
@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500

@app.errorhandler(403)
def forbidden(error):
    return render_template("403.html"), 403
if __name__ == '__main__':
    socketio.run(app)