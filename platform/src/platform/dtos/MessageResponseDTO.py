class MessageResponseDTO:
    def __init__(self, response: str | None = None, error: str | None = None):
        self.response = response
        self.error = error

    def to_dict(self):
        return {
            "response": self.response,
            "error": self.error
        }
