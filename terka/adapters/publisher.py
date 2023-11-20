import json
from dataclasses import asdict
from terka.domain import events
import logging


class BasePublisher:
    ...


class RedisPublisher(BasePublisher):

    def __init__(self,
                 client: "redis.Redis",
                 topic_prefix: str | None = None) -> None:
        self.client = client
        self.topic_prefix = topic_prefix

    def publish(self, topic: str, event: events.Event):
        if self.topic_prefix:
            topic = f"{self.topic_prefix}_{topic}"
        self.client.publish(topic, json.dumps(asdict(event)))


class LogPublisher(BasePublisher):

    def publish(self, topic: str, event: events.Event):
        logging.info("Published to topic '%s': %s", topic, asdict(event))


