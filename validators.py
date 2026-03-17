import re

class ValidationError(Exception):
    pass


class FeedbackValidator:

    MAX_NAME_LENGTH = 100
    MAX_EMAIL_LENGTH = 255
    MAX_MESSAGE_LENGTH = 2000

    EMAIL_REGEX = r"^[^@]+@[^@]+\.[^@]+$"

    @classmethod
    def validate_name(cls, name: str):

        if not name:
            raise ValidationError("Name is required")

        if len(name) > cls.MAX_NAME_LENGTH:
            raise ValidationError("Name too long")

        if not re.match(r"^[a-zA-Z\s\-']+$", name):
            raise ValidationError("Invalid characters in name")

        return name.strip()


    @classmethod
    def validate_email(cls, email: str):

        if not email:
            raise ValidationError("Email is required")

        if len(email) > cls.MAX_EMAIL_LENGTH:
            raise ValidationError("Email too long")

        if not re.match(cls.EMAIL_REGEX, email):
            raise ValidationError("Invalid email format")

        return email.strip().lower()


    @classmethod
    def validate_message(cls, message: str):

        if not message:
            raise ValidationError("Message cannot be empty")

        if len(message) > cls.MAX_MESSAGE_LENGTH:
            raise ValidationError("Message too long")

        return message.strip()