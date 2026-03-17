from models import db, Feedback
from validators import FeedbackValidator
from sanitizers import Sanitizer

class FeedbackService:

    @staticmethod
    def create_feedback(data):

        name = FeedbackValidator.validate_name(data.get("name"))
        email = FeedbackValidator.validate_email(data.get("email"))
        message = FeedbackValidator.validate_message(data.get("message"))

        name = Sanitizer.sanitize_text(name)
        email = Sanitizer.sanitize_text(email)
        message = Sanitizer.sanitize_text(message)

        feedback = Feedback(
            name=name,
            email=email,
            message=message
        )

        db.session.add(feedback)
        db.session.commit()

        return feedback