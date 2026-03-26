import asyncio
import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Awaitable, Callable

from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.kafka.producer import producer

logger = logging.getLogger(__name__)


class KafkaConsumer:
    def __init__(self, topic: str, group_id: str, callback: Callable[[dict], Awaitable[None]]):
        self.topic = topic
        self.group_id = group_id
        self.callback = callback
        self.consumer = None
        self.running = False

    def _build_consumer(self) -> AIOKafkaConsumer:
        return AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=self.group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            max_partition_fetch_bytes=10485760,
            fetch_max_bytes=10485760,
        )

    async def start(self):
        self.running = True
        attempt = 0

        while self.running:
            self.consumer = self._build_consumer()
            try:
                attempt += 1
                await self.consumer.start()
                logger.info(f"Kafka Consumer started for topic: {self.topic}")
                attempt = 0

                async for msg in self.consumer:
                    if not self.running:
                        break

                    raw_payload = None
                    try:
                        raw_payload = msg.value.decode("utf-8")
                        data = json.loads(raw_payload)
                        await self.callback(data)
                        await self.consumer.commit()
                    except Exception as exc:
                        logger.error(f"Error processing message from {self.topic}: {exc}")
                        dlq_sent = await self._send_to_dead_letter(msg, raw_payload, exc)
                        if not dlq_sent:
                            raise
                        await self.consumer.commit()
            except Exception as exc:
                logger.error(
                    f"Kafka Consumer error on topic {self.topic} (attempt {attempt}): {exc}"
                )
                if self._retries_exhausted(attempt):
                    logger.error(
                        f"Kafka Consumer exhausted retries for topic {self.topic}; stopping consumer loop"
                    )
                    break
            finally:
                if self.consumer:
                    await self.consumer.stop()
                    self.consumer = None
                logger.info(f"Kafka Consumer stopped for topic: {self.topic}")

            if self.running:
                await asyncio.sleep(settings.KAFKA_CONNECTION_RETRY_BACKOFF_SEC)

    async def stop(self):
        self.running = False

    @staticmethod
    def _retries_exhausted(attempt: int) -> bool:
        max_retries = settings.KAFKA_CONNECTION_MAX_RETRIES
        return max_retries > 0 and attempt >= max_retries

    async def _send_to_dead_letter(self, msg, raw_payload: str | None, exc: Exception) -> bool:
        dlq_topic = f"{self.topic}{settings.KAFKA_DEAD_LETTER_SUFFIX}"
        payload = {
            "source_topic": self.topic,
            "dead_letter_topic": dlq_topic,
            "consumer_group": self.group_id,
            "partition": msg.partition,
            "offset": msg.offset,
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "payload": raw_payload,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        }

        sent = await producer.send(dlq_topic, payload)
        if sent:
            logger.error(
                f"Sent failed message from {self.topic} partition={msg.partition} offset={msg.offset} to {dlq_topic}"
            )
            return True

        logger.error(
            f"Failed to route message from {self.topic} partition={msg.partition} offset={msg.offset} to {dlq_topic}"
        )
        return False
