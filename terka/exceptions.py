from __future__ import annotations
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


class TerkaInitError(TerkaException):
    ...


class TerkaRefreshException(TerkaException):
    ...


class TerkaSprintOutOfCapacity(TerkaException):
    ...


class TerkaSprintInvalidCapacity(TerkaException):
    ...
