from dataclasses import dataclass

from .composite import Composite


class Epic(Composite):
    ...

@dataclass
class EpicTask:
    epic: int
    task: int
