from datetime import datetime


class BaseNote:

    def __init__(self,
                 name: str,
                 text: str,
                 created_by: int,
                 date: datetime = datetime.now()) -> None:
        self.name = name
        self.text = text
        self.date = date
        self.created_by = created_by

    def __repr__(self):
        return f"<Note> {self.text}"


class TaskNote(BaseNote):

    def __init__(self,
                 id: int,
                 name: str,
                 text: str,
                 created_by: int,
                 date: datetime = datetime.now(),
                 **kwargs: str) -> None:
        self.task = id
        super().__init__(name=name, text=text, created_by=created_by, date=date)


class ProjectNote(BaseNote):

    def __init__(self,
                 id: int,
                 name: str,
                 text: str,
                 created_by: int,
                 date: datetime = datetime.now(),
                 **kwargs: str) -> None:
        self.project = id
        super().__init__(name=name, text=text, created_by=created_by, date=date)


class EpicNote(BaseNote):

    def __init__(self,
                 id: int,
                 name: str,
                 text: str,
                 created_by: int,
                 date: datetime = datetime.now(),
                 **kwargs: str) -> None:
        self.epic = id
        super().__init__(name=name, text=text, created_by=created_by, date=date)


class StoryNote(BaseNote):

    def __init__(self,
                 id: int,
                 name: str,
                 text: str,
                 created_by: int,
                 date: datetime = datetime.now(),
                 **kwargs: str) -> None:
        self.story = id
        super().__init__(name=name, text=text, created_by=created_by, date=date)


class SprintNote(BaseNote):

    def __init__(self,
                 id: int,
                 name: str,
                 text: str,
                 created_by: int,
                 date: datetime = datetime.now(),
                 **kwargs: str) -> None:
        self.sprint = id
        super().__init__(name=name, text=text, created_by=created_by, date=date)
