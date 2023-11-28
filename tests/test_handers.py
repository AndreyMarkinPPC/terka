import pytest
from terka import bootstrap
from terka.adapters import publisher
from terka.domain import _commands, models


class FakePublisher(publisher.BasePublisher):

    def __init__(self):
        self.events = []  # type: Dict[str, List[str]]

    def publish(self, topic, event):
        self.events.append(event)


@pytest.fixture(scope="module")
def fake_publisher():
    return FakePublisher()


@pytest.fixture
def bus(fake_publisher, uow):
    return bootstrap.bootstrap(start_orm=True,
                               uow=uow,
                               publish_service=fake_publisher)


class TestTask:

    def test_create_simple_task(self, bus):
        cmd = _commands.CreateTask(name="test")
        bus.handle(cmd)
        new_task = bus.handler.uow.tasks.get_by_id(models.task.Task, 1)
        assert new_task.name == "test"
