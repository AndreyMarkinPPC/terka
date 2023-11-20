class TerkaException(Exception):
    ...


class TerkaCommandException(TerkaException):
    ...


class TaskAddedToCompletedEntity(TerkaException):
    ...


class TaskAddedToEntity(TerkaException):
    ...


class EntityNotFound(TerkaException):
    ...


class TerkaSprintEndDateInThePast(TerkaException):
    ...


class TerkaSprintCompleted(TerkaException):
    ...


class TerkaSprintActive(TerkaException):
    ...
