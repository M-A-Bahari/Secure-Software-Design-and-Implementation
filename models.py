from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    first_name = db.Column(db.String(100), nullable=False, default="")
    last_name = db.Column(db.String(100), nullable=False, default="")

    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    role = db.Column(db.String(20), default="user", nullable=False)

    security_answer1 = db.Column(db.String(200), nullable=False)
    security_answer2 = db.Column(db.String(200), nullable=False)
    security_answer3 = db.Column(db.String(200), nullable=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    failed_logins = db.Column(db.Integer, default=0)
    last_login = db.Column(db.DateTime)
    locked_until = db.Column(db.DateTime, nullable=True)
    lockout_count = db.Column(db.Integer, default=0, nullable=False)
    last_lockout_minutes = db.Column(db.Integer, default=0, nullable=False)
    feedback_count = db.Column(db.Integer, default=0, nullable=False)
    feedback_date = db.Column(db.Date, nullable=True)

    def set_password(self, password: str):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str):
        return bcrypt.check_password_hash(self.password_hash, password)

    def set_security_answers(self, answer1: str, answer2: str, answer3: str):
        self.security_answer1 = bcrypt.generate_password_hash(answer1.lower().strip()).decode("utf-8")
        self.security_answer2 = bcrypt.generate_password_hash(answer2.lower().strip()).decode("utf-8")
        self.security_answer3 = bcrypt.generate_password_hash(answer3.lower().strip()).decode("utf-8")

    def check_security_answer(self, answer: str, stored_hash: str) -> bool:
        try:
            return bcrypt.check_password_hash(stored_hash, answer.lower().strip())
        except ValueError:
            return False
    
class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(120), nullable=False)

    email = db.Column(db.String(255), nullable=False)

    message = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now())