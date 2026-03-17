import html

class Sanitizer:

    @staticmethod
    def sanitize_text(text: str) -> str:
        return html.escape(text)