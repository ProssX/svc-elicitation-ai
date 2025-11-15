import asyncio
import logging
import signal
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.clients.backend_client import BackendClient
from app.repositories.interview_repository import InterviewRepository
from app.services.process_extraction_service import ProcessExtractionService
from app.utils.event_bus import get_event_bus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

shutdown_event = asyncio.Event()


def handle_shutdown(signum, frame):
    logger.info("Shutdown signal received")
    shutdown_event.set()


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


async def process_interview_completed(event: Dict[str, Any]):
    async with AsyncSessionLocal() as db:
        try:
            interview_id = event["data"]["interview_id"]
            organization_id = event["data"]["organization_id"]
            auth_token = event["data"]["auth_token"]
            
            logger.info(
                f"Processing interview.completed event",
                extra={
                    "interview_id": interview_id,
                    "organization_id": organization_id,
                    "timestamp": event.get("timestamp")
                }
            )
            
            backend_client = BackendClient()
            interview_repository = InterviewRepository(db)
            
            extraction_service = ProcessExtractionService(
                db=db,
                backend_client=backend_client,
                interview_repository=interview_repository
            )
            
            await extraction_service.extract_and_create_processes(
                interview_id=interview_id,
                organization_id=organization_id,
                auth_token=auth_token
            )
            
            await db.commit()
            
            logger.info(
                f"Successfully processed interview {interview_id}",
                extra={"interview_id": interview_id}
            )
        
        except Exception as e:
            await db.rollback()
            logger.error(
                f"Failed to process interview.completed event: {e}",
                extra={"event": event, "error": str(e)},
                exc_info=True
            )


async def main():
    logger.info("Starting process extraction worker")
    
    event_bus = get_event_bus()
    
    try:
        await event_bus.connect()
        logger.info("Worker connected to event bus")
        
        subscribe_task = asyncio.create_task(
            event_bus.subscribe("interview.completed", process_interview_completed)
        )
        
        await shutdown_event.wait()
        
        logger.info("Shutting down worker gracefully")
        subscribe_task.cancel()
        
        try:
            await subscribe_task
        except asyncio.CancelledError:
            pass
        
        await event_bus.disconnect()
        logger.info("Worker stopped")
    
    except Exception as e:
        logger.error(f"Worker crashed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
