from datetime import datetime


class Commentary:

    def __init__(self,
                 element_id: int,
                 text: str,
                 source: str = "tasks",
                 date: datetime = datetime.now(),
                 **kwargs):
        self.source = source
        self.element_id = element_id
        self.text = text
        self.date = date

    def __repr__(self):
        return f"<Commentary> {self.text}"
