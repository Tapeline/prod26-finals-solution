class AppException(Exception):
    def __init__(self) -> None:
        if hasattr(self, "text"):
            super().__init__(self.text)


class NotAuthenticated(AppException):
    text = "Not authenticated"
