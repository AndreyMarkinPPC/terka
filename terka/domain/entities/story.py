from dataclasses import dataclass

from .composite import Composite


class Story(Composite):
    ...


@dataclass
class StoryTask:
    story: int
    task: int
