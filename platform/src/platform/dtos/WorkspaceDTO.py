class WorkspaceDTO:
    def __init__(self, workspace):
        self.id = workspace.id
        self.name = workspace.name

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }
