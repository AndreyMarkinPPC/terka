from typing import Any, Callable, Dict, Type


from terka.domain import _commands, events
from terka.service_layer import unit_of_work


Message = _commands.Command | events.Event

class MessageBus:
    def __init__(
        self,
        uow: unit_of_work.AbstractUnitOfWork,
        event_handlers: dict[Type[events.Event], Callable],
        command_handlers: dict[Type[_commands.Command], Callable]
    ) -> None:
        self.uow = uow
        self.event_handlers = event_handlers
        self.command_handlers = command_handlers
        self.return_value = None

    def handle(self, message: Message):
        self.queue = [message]
        while self.queue:
            message = self.queue.pop(0)
            if isinstance(message, events.Event):
                self.handle_event(message)
            elif isinstance(message, _commands.Command):
                self.handle_command(message)

        if self.return_value:
            return self.return_value

    def handle_command(self, command: _commands.Command) -> None:
        handler = self.command_handlers[type(command)]
        result = handler(command)
        self.return_value = result
        self.queue.extend(self.uow.collect_new_events())

    def handle_event(self, event: events.Event) -> None:
        for handler in self.event_handlers[type(event)]:
            handler(event)
            self.queue.extend(self.uow.collect_new_events())

