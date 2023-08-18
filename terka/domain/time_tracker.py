from datetime import datetime


class TimeTrackerEntry:

    def __init__(self,
                 task: int,
                 time_spent_minutes: float,
                 creation_date: datetime = datetime.now(),
                 **kwargs):
        if not isinstance(creation_date, datetime):
            raise ValueError(
                "creation_date should be of type datetime.datetime!")
        self.task = task
        self.time_spent_minutes = time_spent_minutes
        self.creation_date = creation_date

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}> [{self.creation_date.strftime('%Y-%m-%d %H:%M')}] "
            f"{self.time_spent_minutes} min")
