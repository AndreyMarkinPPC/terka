class BaseTag:

    def __init__(self, text: str, **kwargs: str) -> None:
        self.text = text

    def __repr__(self):
        return f"<Tag> {self.text}"


class TaskTag(BaseTag):

    def __init__(self,
                 id: int,
                 text: str,
                 **kwargs: str) -> None:
        self.task = id
        super().__init__(text=text)


class ProjectTag(BaseTag):

    def __init__(self,
                 id: int,
                 text: str,
                 **kwargs: str) -> None:
        self.project = id
        super().__init__(text=text)
