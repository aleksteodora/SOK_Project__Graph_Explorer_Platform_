class MessageDTO:
    def __init__(self, text: str, type: str):
        self.text = text
        self.type = type

    def to_dict(self):
        return {
            "text": self.text,
            "type": self.type
        }
