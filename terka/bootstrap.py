import inspect

from terka.adapters import orm, publisher
from terka.service_layer import handlers, messagebus, unit_of_work


def bootstrap(
    uow: unit_of_work.AbstractUnitOfWork,
    start_orm: bool = True,
    publish_service: publisher.BasePublisher = publisher.LogPublisher()
) -> messagebus.MessageBus:

    if start_orm:
        orm.start_mappers(engine=uow.engine)

    dependencies = {
        "uow": uow,
        "publisher": publish_service
    }
    injected_event_handlers = {
        event_type:
        [inject_dependencies(handler, dependencies) for handler in handlers]
        for event_type, handlers in handlers.EVENT_HANDLERS.items()
    }
    injected_command_handlers = {
        command_type: inject_dependencies(handler, dependencies)
        for command_type, handler in handlers.COMMAND_HANDLERS.items()
    }
    return messagebus.MessageBus(uow=uow,
                                 event_handlers=injected_event_handlers,
                                 command_handlers=injected_command_handlers)


def inject_dependencies(handler, dependencies):
    params = inspect.signature(handler).parameters
    deps = {
        name: dependency
        for name, dependency in dependencies.items() if name in params
    }
    return lambda message: handler(message, **deps)

