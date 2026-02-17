import re
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from models import db, User

auth_bp = Blueprint("auth", __name__)

def password_ok(pw: str) -> bool:
    # Simple UG policy (upgrade later if needed)
    if len(pw) < 8:
        return False
    if not re.search(r"[A-Z]", pw):
        return False
    if not re.search(r"[0-9]", pw):
        return False
    return True

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if len(username) < 3:
            flash("Username must be at least 3 characters.")
            return redirect(url_for("auth.register"))

        if not password_ok(password):
            flash("Password must be 8+ chars, include 1 uppercase and 1 number.")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect(url_for("auth.register"))

        user = User(username=username, role="user")
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Account created. Please log in.")
        return redirect(url_for("auth.login"))

    return render_template("register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        # Generic message prevents username enumeration
        if not user or not user.check_password(password):
            flash("Invalid credentials.")
            return redirect(url_for("auth.login"))

        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))