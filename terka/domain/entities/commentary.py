from datetime import datetime


class BaseCommentary:

    def __init__(self, text: str, date: datetime = datetime.now(), **kwargs: str) -> None:
        self.text = text
        self.date = date

    def __repr__(self):
        return f"<Commentary> {self.text}"


class TaskCommentary(BaseCommentary):

    def __init__(self,
                 id: int,
                 text: str,
                 date: datetime = datetime.now(), **kwargs: str) -> None:
        self.task = id
        super().__init__(text=text,
                         date=date)


class ProjectCommentary(BaseCommentary):

    def __init__(self, id: int,
                 text: str,
                 date: datetime = datetime.now(), **kwargs: str) -> None:
        self.project = id
        super().__init__(text=text,
                         date=date)


class EpicCommentary(BaseCommentary):

    def __init__(self, id: int,
                 text: str,
                 date: datetime = datetime.now(), **kwargs: str) -> None:
        self.epic = id
        super().__init__(text=text,
                         date=date)


class StoryCommentary(BaseCommentary):

    def __init__(self, id: int,
                 text: str,
                 date: datetime = datetime.now(), **kwargs: str) -> None:
        self.story = id
        super().__init__(text=text,
                         date=date)


class SprintCommentary(BaseCommentary):

    def __init__(self, id: int,
                 text: str,
                 date: datetime = datetime.now(), **kwargs: str) -> None:
        self.sprint = id
        super().__init__(text=text,
                         date=date)
