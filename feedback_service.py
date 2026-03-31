from models import db, Feedback
from validators import FeedbackValidator
from sanitizers import Sanitizer

class FeedbackService:

    @staticmethod
    def create_feedback(data, user):

        email = FeedbackValidator.validate_email(data.get("email"))
        message = FeedbackValidator.validate_message(data.get("message"))

        email = Sanitizer.sanitize_text(email)
        message = Sanitizer.sanitize_text(message)

        feedback = Feedback(
            username=data.get("username"),
            email=email,
            message=message
        )

        db.session.add(feedback)
        user.feedback_count += 1
        db.session.commit()

        return feedback