from datetime import datetime

from .project import Project


class User:

    def __init__(self, name: str, **kwargs):
        self.name = name

    def __repr__(self):
        return f"<User {self.name}>"

    def __eq__(self, other):
       if not isinstance(other, User):
           return False
       return other.name == self.name
