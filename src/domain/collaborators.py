class CollaboratorMixin:
    def __repr__(self):
        return f"<Collaborator> {self.id}"


class TaskCollaborator(CollaboratorMixin):

    def __init__(self,
                 id: int,
                 collaborator_id: int,
                 **kwargs: str) -> None:
        self.task = id
        self.collaborator = collaborator_id


class ProjectCollaborator(CollaboratorMixin):

    def __init__(self,
                 id: int,
                 collaborator_id: int,
                 **kwargs: str) -> None:
        self.project = id
        self.collaborator = collaborator_id

