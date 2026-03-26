import asyncio
import json
import logging

from aiokafka import AIOKafkaProducer

from app.core.config import settings

logger = logging.getLogger(__name__)


class KafkaProducer:
    def __init__(self):
        self.producer = None
        self._start_lock = asyncio.Lock()

    async def start(self, force_restart: bool = False) -> bool:
        if self.producer and not force_restart:
            return True

        async with self._start_lock:
            if self.producer and not force_restart:
                return True

            if force_restart and self.producer:
                await self._stop_producer()

            attempt = 0
            while True:
                attempt += 1
                candidate = AIOKafkaProducer(
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                    max_request_size=10485760,
                )
                try:
                    await candidate.start()
                    self.producer = candidate
                    logger.info("Kafka Producer started")
                    return True
                except Exception as exc:
                    logger.error(
                        f"Failed to start Kafka Producer (attempt {attempt}): {exc}"
                    )
                    try:
                        await candidate.stop()
                    except Exception:
                        pass

                    if self._retries_exhausted(attempt):
                        self.producer = None
                        return False

                    await asyncio.sleep(settings.KAFKA_CONNECTION_RETRY_BACKOFF_SEC)

    async def stop(self):
        async with self._start_lock:
            await self._stop_producer()

    async def send(self, topic: str, value: dict) -> bool:
        if not self.producer:
            started = await self.start()
            if not started:
                logger.error("Kafka Producer is not running")
                return False

        if not self.producer:
            logger.error("Kafka Producer is not running")
            return False

        try:
            await self.producer.send_and_wait(
                topic,
                json.dumps(value).encode("utf-8"),
            )
            return True
        except Exception as exc:
            logger.error(f"Failed to send message to {topic}: {exc}")

        restarted = await self.start(force_restart=True)
        if not restarted or not self.producer:
            logger.error(f"Kafka Producer could not recover before retrying topic {topic}")
            return False

        try:
            await self.producer.send_and_wait(
                topic,
                json.dumps(value).encode("utf-8"),
            )
            return True
        except Exception as exc:
            logger.error(f"Retry send failed for topic {topic}: {exc}")
            return False

    async def _stop_producer(self) -> None:
        if self.producer:
            await self.producer.stop()
            self.producer = None
            logger.info("Kafka Producer stopped")

    @staticmethod
    def _retries_exhausted(attempt: int) -> bool:
        max_retries = settings.KAFKA_CONNECTION_MAX_RETRIES
        return max_retries > 0 and attempt >= max_retries


producer = KafkaProducer()
