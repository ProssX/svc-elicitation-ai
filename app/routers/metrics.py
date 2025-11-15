"""
Metrics Router
Exposes metrics for monitoring

Provides two types of metrics:
- Real-time: In-memory metrics for current session (fast)
- Historical: PostgreSQL metrics for trend analysis (persistent)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.metrics_service import get_metrics_collector
from app.repositories.metrics_repository import MetricsRepository
from app.models.responses import StandardResponse

router = APIRouter(prefix="/api/v1/metrics", tags=["Metrics"])


@router.get("/detection", response_model=StandardResponse)
async def get_detection_metrics():
    """
    Get process detection metrics
    
    Returns metrics about process detection performance:
    - Invocation count and rate
    - Success, timeout, and error rates
    - Latency percentiles (p50, p95, p99)
    - Average confidence score
    """
    metrics = get_metrics_collector()
    detection_metrics = metrics.get_detection_metrics()
    
    return StandardResponse(
        status="success",
        code=200,
        message="Detection metrics retrieved successfully",
        data=detection_metrics
    )


@router.get("/completion", response_model=StandardResponse)
async def get_completion_metrics():
    """
    Get interview completion metrics
    
    Returns metrics about interview completion:
    - Interviews started and completed
    - Completion rate
    - Early finish rate
    - User requested, agent signaled, and safety limit rates
    - Average question count
    """
    metrics = get_metrics_collector()
    completion_metrics = metrics.get_completion_metrics()
    
    return StandardResponse(
        status="success",
        code=200,
        message="Completion metrics retrieved successfully",
        data=completion_metrics
    )


@router.get("", response_model=StandardResponse)
async def get_all_metrics():
    """
    Get all metrics
    
    Returns all available metrics including:
    - System uptime
    - Process detection metrics
    - Interview completion metrics
    """
    metrics = get_metrics_collector()
    all_metrics = metrics.get_all_metrics()
    
    return StandardResponse(
        status="success",
        code=200,
        message="All metrics retrieved successfully",
        data=all_metrics
    )


@router.post("/reset", response_model=StandardResponse)
async def reset_metrics():
    """
    Reset all in-memory metrics
    
    Clears all collected in-memory metrics and resets counters to zero.
    Note: This only resets in-memory metrics, not database records.
    Use with caution - this will lose all current session data.
    """
    metrics = get_metrics_collector()
    metrics.reset()
    
    return StandardResponse(
        status="success",
        code=200,
        message="All in-memory metrics reset successfully",
        data={"reset": True}
    )


@router.get("/detection/historical", response_model=StandardResponse)
async def get_detection_metrics_historical(
    hours: int = Query(default=24, ge=1, le=720, description="Time window in hours (1-720)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get historical process detection metrics from database
    
    Args:
        hours: Time window in hours (default 24h, max 30 days)
        
    Returns metrics about process detection performance from PostgreSQL:
    - Invocation count
    - Success, timeout, and error rates
    - Average/min/max latency
    - Average confidence score
    - Time window
    """
    repo = MetricsRepository(db)
    metrics = await repo.get_detection_metrics(hours=hours)
    percentiles = await repo.get_detection_percentiles(hours=hours)
    
    # Merge percentiles into metrics
    metrics.update(percentiles)
    
    return StandardResponse(
        status="success",
        code=200,
        message=f"Historical detection metrics retrieved for last {hours}h",
        data=metrics
    )


@router.get("/completion/historical", response_model=StandardResponse)
async def get_completion_metrics_historical(
    hours: int = Query(default=24, ge=1, le=720, description="Time window in hours (1-720)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get historical interview completion metrics from database
    
    Args:
        hours: Time window in hours (default 24h, max 30 days)
        
    Returns metrics about interview completion from PostgreSQL:
    - Interviews started and completed
    - Completion rate
    - Early finish rate
    - User requested, agent signaled, and safety limit rates
    - Average question count
    - Time window
    """
    repo = MetricsRepository(db)
    metrics = await repo.get_completion_metrics(hours=hours)
    
    return StandardResponse(
        status="success",
        code=200,
        message=f"Historical completion metrics retrieved for last {hours}h",
        data=metrics
    )


@router.get("/historical", response_model=StandardResponse)
async def get_all_metrics_historical(
    hours: int = Query(default=24, ge=1, le=720, description="Time window in hours (1-720)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all historical metrics from database
    
    Args:
        hours: Time window in hours (default 24h, max 30 days)
        
    Returns all available historical metrics from PostgreSQL:
    - Process detection metrics with percentiles
    - Interview completion metrics
    """
    repo = MetricsRepository(db)
    
    detection_metrics = await repo.get_detection_metrics(hours=hours)
    detection_percentiles = await repo.get_detection_percentiles(hours=hours)
    completion_metrics = await repo.get_completion_metrics(hours=hours)
    
    # Merge percentiles into detection metrics
    detection_metrics.update(detection_percentiles)
    
    return StandardResponse(
        status="success",
        code=200,
        message=f"All historical metrics retrieved for last {hours}h",
        data={
            "time_window_hours": hours,
            "detection": detection_metrics,
            "completion": completion_metrics
        }
    )
