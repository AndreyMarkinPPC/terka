import abc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from terka.adapters import repository
from terka.domain import events


class AbstractUnitOfWork(abc.ABC):
    tasks: repository.AbsRepository
    published_events: list[events.Event] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.rollback()

    def commit(self):
        self._commit()

    def flush(self):
        self._flush()

    def collect_new_events(self):
        while self.published_events:
            yield self.published_events.pop(0)

    @abc.abstractmethod
    def _commit(self):
        ...

    @abc.abstractmethod
    def _flush(self):
        ...

    @abc.abstractmethod
    def rollback(self):
        ...


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):

    def __init__(self, session_factory) -> None:
        self.engine = create_engine(session_factory)
        self.session_factory = sessionmaker(self.engine)
        self.published_events: list[events.Event] = []

    @property
    def repo(self):
        return repository.SqlAlchemyRepository(self.session_factory())

    def __enter__(self) -> None:
        self.session = self.session_factory()  # type: Session
        self.tasks = repository.SqlAlchemyRepository(self.session)
        return super().__enter__()

    def __exit__(self, *args):
        super().__exit__(*args)
        self.session.close()

    def _commit(self):
        self.session.commit()

    def _flush(self):
        self.session.flush()

    def rollback(self):
        self.session.rollback()
