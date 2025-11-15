import redis.asyncio as redis
import json
import logging
from typing import Dict, Any, Callable, Awaitable
from datetime import datetime

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client = None
        self.pubsub = None
    
    async def connect(self):
        if self.redis_client is None:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Connected to Redis event bus", extra={"redis_url": self.redis_url})
    
    async def disconnect(self):
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.aclose()
        if self.redis_client:
            await self.redis_client.aclose()
            logger.info("Disconnected from Redis event bus")
    
    async def publish(self, event_type: str, data: Dict[str, Any]):
        await self.connect()
        
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            await self.redis_client.publish(
                channel=f"events:{event_type}",
                message=json.dumps(event)
            )
            logger.info(
                f"Published event: {event_type}",
                extra={"event_type": event_type, "event_data": data}
            )
        except Exception as e:
            logger.error(
                f"Failed to publish event {event_type}: {e}",
                extra={"event_type": event_type, "error": str(e)}
            )
            raise
    
    async def subscribe(
        self,
        event_type: str,
        callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ):
        await self.connect()
        
        self.pubsub = self.redis_client.pubsub()
        await self.pubsub.subscribe(f"events:{event_type}")
        
        logger.info(f"Subscribed to event: {event_type}", extra={"event_type": event_type})
        
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                try:
                    event = json.loads(message["data"])
                    await callback(event)
                except json.JSONDecodeError as e:
                    logger.error(
                        f"Invalid JSON in event: {e}",
                        extra={"event_type": event_type, "raw_data": message["data"]}
                    )
                except Exception as e:
                    logger.error(
                        f"Error processing event {event_type}: {e}",
                        extra={"event_type": event_type, "error": str(e)},
                        exc_info=True
                    )


_event_bus_instance = None


def get_event_bus() -> EventBus:
    global _event_bus_instance
    if _event_bus_instance is None:
        from app.config import settings
        _event_bus_instance = EventBus(settings.redis_url)
    return _event_bus_instance
