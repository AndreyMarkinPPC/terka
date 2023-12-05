class BaseTag:

    def __init__(self, text: str, **kwargs: str) -> None:
        self.text = text

    def __repr__(self):
        return f"<Tag> {self.text}"


class TagMixin:
    def __repr__(self):
        return f"{self.base_tag.text}"


class TaskTag(TagMixin):

    def __init__(self,
                 id: int,
                 tag_id: int,
                 **kwargs: str) -> None:
        self.task = id
        self.tag= tag_id


class ProjectTag(TagMixin):

    def __init__(self,
                 id: int,
                 tag_id: int,
                 **kwargs: str) -> None:
        self.project = id
        self.tag= tag_id
