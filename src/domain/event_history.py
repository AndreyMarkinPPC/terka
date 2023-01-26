from dataclasses import dataclass
from datetime import datetime


@dataclass
class Event:
    source: str
    element_id: int
    date: datetime
    type: str
    old_value: str
    new_value: str
