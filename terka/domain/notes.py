from datetime import datetime


class BaseNote:

    def __init__(self, text: str, date: datetime = datetime.now()) -> None:
        self.text = text
        self.date = date

    def __repr__(self):
        return f"<Note> {self.text}"


class TaskNote(BaseNote):

    def __init__(self,
                 id: int,
                 text: str,
                 date: datetime = datetime.now(), **kwargs: str) -> None:
        self.task = id
        super().__init__(text=text,
                         date=date)


class ProjectNote(BaseNote):

    def __init__(self, id: int,
                 text: str,
                 date: datetime = datetime.now(), **kwargs: str) -> None:
        self.project = id
        super().__init__(text=text,
                         date=date)


class EpicNote(BaseNote):

    def __init__(self, id: int,
                 text: str,
                 date: datetime = datetime.now(), **kwargs: str) -> None:
        self.epic = id
        super().__init__(text=text,
                         date=date)


class StoryNote(BaseNote):

    def __init__(self, id: int,
                 text: str,
                 date: datetime = datetime.now(), **kwargs: str) -> None:
        self.story = id
        super().__init__(text=text,
                         date=date)


class SprintNote(BaseNote):

    def __init__(self, id: int,
                 text: str,
                 date: datetime = datetime.now(), **kwargs: str) -> None:
        self.sprint = id
        super().__init__(text=text,
                         date=date)
