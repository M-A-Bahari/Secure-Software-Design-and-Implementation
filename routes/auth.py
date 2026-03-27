import re
import random
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required
from models import db, User

auth_bp = Blueprint("auth", __name__)

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_TIME = timedelta(minutes=5)


def password_ok(pw: str):
    if len(pw) < 8:
        return False
    if not re.search(r"[A-Z]", pw):
        return False
    if not re.search(r"[0-9]", pw):
        return False
    if not re.search(r"[\x21-\x2F\x3A-\x40\x5B-\x60\x7B-\x7E]", pw):
        return False
    return True


#Registration route

@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        answer1 = request.form.get("answer1", "").lower().strip()
        answer2 = request.form.get("answer2", "").lower().strip()
        answer3 = request.form.get("answer3", "").lower().strip()

        if not first_name or not last_name:
            flash("First and last name are required.", "error")
            return redirect(url_for("auth.register"))

        if len(username) < 3:
            flash("Username must be at least 3 characters.", "error")
            return redirect(url_for("auth.register"))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("auth.register"))

        if not password_ok(password):
            flash("Password must be 8+ chars, include at least 1 uppercase, 1 number & 1 symbol.", "error")
            return redirect(url_for("auth.register"))

        pw_lower = password.lower()
        name_parts = [p for p in [first_name.lower(), last_name.lower()] if len(p) >= 3]
        for part in name_parts:
            if part in pw_lower:
                flash(f"Password must not contain your first or last name.", "error")
                return redirect(url_for("auth.register"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "error")
            return redirect(url_for("auth.register"))

        user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            role="user",
            security_answer1=answer1,
            security_answer2=answer2,
            security_answer3=answer3
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Account created. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


#Login route

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user:

            # Check if account is locked
            if user.failed_logins >= MAX_LOGIN_ATTEMPTS:

                if user.last_login and datetime.utcnow() - user.last_login < LOCKOUT_TIME:
                    flash("Account locked. Try again in 5 minutes.", "error")
                    return redirect(url_for("auth.login"))

                # Unlock after timeout
                user.failed_logins = 0
                db.session.commit()

        if not user or not user.check_password(password):

            if user:
                user.failed_logins += 1
                user.last_login = datetime.utcnow()
                db.session.commit()

                remaining = MAX_LOGIN_ATTEMPTS - user.failed_logins

                if remaining > 0:
                    flash(f"Invalid credentials. {remaining} attempts remaining.", "error")
                else:
                    flash("Account locked for 5 minutes due to too many failed login attempts.", "error")

            else:
                flash("Invalid credentials.", "error")

            return redirect(url_for("auth.login"))

        # Successful login
        user.failed_logins = 0
        user.last_login = datetime.utcnow()

        db.session.commit()

        login_user(user)

        return redirect(url_for("dashboard"))

    return render_template("login.html")


#Logout route

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


# Password reset routes

@auth_bp.route("/verify_username", methods=["GET", "POST"])
def verify_username():

    if request.method == "POST":

        username = request.form.get("username", "").strip()

        user = User.query.filter_by(username=username).first()

        if not user:
            flash("Sorry, we could not verify your identity.", "error")
            return redirect(url_for("auth.login"))

        session["reset_user"] = user.id
        session["reset_token"] = secrets.token_hex(16)
        session["reset_step"] = "security_question"

        session.pop("current_question", None)
        session.pop("correct_answer", None)
        session.pop("attempts", None)
        session.pop("reset_verified", None)

        return redirect(url_for("auth.security_question"))

    return render_template("verify_username.html")


#security question route

@auth_bp.route("/security_question", methods=["GET", "POST"])
def security_question():

    user_id = session.get("reset_user")
    token = session.get("reset_token")

    if not user_id or not token or session.get("reset_step") != "security_question":
        return redirect(url_for("auth.login"))

    user = User.query.get(user_id)

    if "current_question" not in session:

        questions = [
            ("First pet's name?", user.security_answer1),
            ("Elementary school you attended?", user.security_answer2),
            ("City you were born in?", user.security_answer3)
        ]

        question = random.choice(questions)

        session["current_question"] = question[0]
        session["correct_answer"] = question[1]
        session["attempts"] = 0

    question_text = session["current_question"]
    correct_answer = session["correct_answer"]

    if request.method == "POST":

        answer = request.form.get("answer", "").lower().strip()

        session["attempts"] += 1

        if session["attempts"] > 3:

            flash("Too many incorrect attempts. Please start the recovery process again.", "error")

            session.clear()

            return redirect(url_for("auth.login"))

        if answer != correct_answer:

            flash("Incorrect answer. Try again.", "error")

            return render_template(
                "security_question.html",
                question=question_text
            )

        if session["attempts"] == 1:

            session["reset_step"] = "reset_password"
            return redirect(url_for("auth.reset_password"))

        else:

            session.pop("current_question", None)
            session.pop("correct_answer", None)
            session["attempts"] = 0

            flash("Correct. Please answer another security question.", "info")

            return redirect(url_for("auth.security_question"))

    return render_template("security_question.html", question=question_text)


#Reset password route

@auth_bp.route("/reset_password", methods=["GET", "POST"])
def reset_password():

    user_id = session.get("reset_user")
    token = session.get("reset_token")

    if not user_id or not token or session.get("reset_step") != "reset_password":
        flash("Unauthorized password reset attempt.", "error")
        return redirect(url_for("auth.login"))

    user = User.query.get(user_id)

    if request.method == "POST":

        new_password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if new_password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("reset_password.html")

        if not password_ok(new_password):
            flash("Password must be 8+ chars, include at least 1 uppercase, 1 number & 1 symbol.", "error")
            return render_template("reset_password.html")

        user.set_password(new_password)
        user.failed_logins = 0

        db.session.commit()

        flash("Password reset successful. You may now login.", "success")

        session.clear()

        return redirect(url_for("auth.login"))

    return render_template("reset_password.html")