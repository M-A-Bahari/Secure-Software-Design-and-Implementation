from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager, login_required, current_user
from dotenv import load_dotenv

from config import Config
from models import db, bcrypt, User
from routes.auth import auth_bp
from routes.feedback_routes import feedback_bp


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(feedback_bp)

    # Home route
    @app.route("/")
    def home():
        return redirect(
            url_for("dashboard") if current_user.is_authenticated else url_for("auth.login")
        )

    # Dashboard
    @app.route("/dashboard")
    @login_required
    def dashboard():
        return render_template(
            "dashboard.html",
            username=current_user.username
        )

    # Create database tables
    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    import os
    app = create_app()
    app.run(debug=os.getenv("FLASK_ENV") == "development")