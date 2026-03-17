from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

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

    def set_password(self, password: str):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str):
        return bcrypt.check_password_hash(self.password_hash, password)
    
class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(255), nullable=False)

    message = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now())