class PluginDTO:
    def __init__(self, plugin):
        self.id = plugin.id
        self.name = plugin.name

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }
