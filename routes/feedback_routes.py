from datetime import date
from flask import Blueprint, request, render_template
from flask_login import login_required, current_user
from feedback_service import FeedbackService
from validators import ValidationError
from models import db

feedback_bp = Blueprint("feedback", __name__)

MAX_FEEDBACK_SUBMISSIONS = 5


@feedback_bp.route("/feedback-page", methods=["GET"])
@login_required
def feedback_page():
    return render_template("feedback.html")


@feedback_bp.route("/feedback", methods=["POST"])
@login_required
def submit_feedback():
    try:
        today = date.today()

        # Reset count if it's a new day
        if current_user.feedback_date != today:
            current_user.feedback_count = 0
            current_user.feedback_date = today
            db.session.commit()

        if current_user.feedback_count >= MAX_FEEDBACK_SUBMISSIONS:
            return render_template(
                "feedback.html",
                error=f"You have reached the maximum of {MAX_FEEDBACK_SUBMISSIONS} feedback submissions."
            )

        # Get data from HTML form
        data = {
            "email": request.form.get("email"),
            "message": request.form.get("message"),
            "username": current_user.username
        }

        # Send to service layer
        FeedbackService.create_feedback(data, current_user)

        # Show success message on the same page
        return render_template(
            "feedback.html",
            success="Feedback submitted successfully!"
        )

    except ValidationError as e:
        return render_template(
            "feedback.html",
            error=str(e)
        )

    except Exception:
        return render_template(
            "feedback.html",
            error="Unexpected error occurred"
        )