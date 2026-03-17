from flask import Blueprint, request, render_template
from feedback_service import FeedbackService
from validators import ValidationError

feedback_bp = Blueprint("feedback", __name__)


@feedback_bp.route("/feedback-page", methods=["GET"])
def feedback_page():
    return render_template("feedback.html")


@feedback_bp.route("/feedback", methods=["POST"])
def submit_feedback():
    try:
        # Get data from HTML form
        data = {
            "name": request.form.get("name"),
            "email": request.form.get("email"),
            "message": request.form.get("message")
        }

        # Send to service layer
        FeedbackService.create_feedback(data)

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