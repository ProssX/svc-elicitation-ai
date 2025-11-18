"""
Metrics Repository
Handles database operations for MetricEvent entities
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import MetricEvent, MetricTypeEnum, MetricOutcomeEnum


class MetricsRepository:
    """Repository for Metrics CRUD and aggregation operations"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session
        
        Args:
            db: Async SQLAlchemy session
        """
        self.db = db
    
    async def save_event(self, event: MetricEvent) -> MetricEvent:
        """
        Save a metric event to the database
        
        Args:
            event: MetricEvent instance to persist
            
        Returns:
            Saved metric event with generated ID
        """
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event
    
    async def get_detection_metrics(
        self, 
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get process detection performance metrics for the last N hours
        
        Args:
            hours: Time window in hours (default 24h)
            
        Returns:
            Dictionary with detection metrics:
            - invocation_count: Total detections
            - success_rate: % successful
            - timeout_rate: % timeouts
            - error_rate: % errors
            - avg_latency_ms: Average latency
            - min_latency_ms: Minimum latency
            - max_latency_ms: Maximum latency
            - avg_confidence_score: Average confidence (successful only)
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Query for detection events in time window
        stmt = select(
            func.count(MetricEvent.id_event).label('total_count'),
            func.sum(case((MetricEvent.outcome == MetricOutcomeEnum.success, 1), else_=0)).label('success_count'),
            func.sum(case((MetricEvent.outcome == MetricOutcomeEnum.timeout, 1), else_=0)).label('timeout_count'),
            func.sum(case((MetricEvent.outcome == MetricOutcomeEnum.error, 1), else_=0)).label('error_count'),
            func.avg(MetricEvent.latency_ms).label('avg_latency'),
            func.min(MetricEvent.latency_ms).label('min_latency'),
            func.max(MetricEvent.latency_ms).label('max_latency'),
            func.avg(
                case((MetricEvent.outcome == MetricOutcomeEnum.success, MetricEvent.confidence_score), else_=None)
            ).label('avg_confidence')
        ).where(
            and_(
                MetricEvent.event_type == MetricTypeEnum.detection_invoked,
                MetricEvent.occurred_at >= cutoff_time
            )
        )
        
        result = await self.db.execute(stmt)
        row = result.one()
        
        total = row.total_count or 0
        success = row.success_count or 0
        timeout = row.timeout_count or 0
        error = row.error_count or 0
        
        return {
            'invocation_count': total,
            'success_rate': round(success / total, 4) if total > 0 else 0.0,
            'timeout_rate': round(timeout / total, 4) if total > 0 else 0.0,
            'error_rate': round(error / total, 4) if total > 0 else 0.0,
            'avg_latency_ms': round(float(row.avg_latency), 2) if row.avg_latency else 0.0,
            'min_latency_ms': round(float(row.min_latency), 2) if row.min_latency else 0.0,
            'max_latency_ms': round(float(row.max_latency), 2) if row.max_latency else 0.0,
            'avg_confidence_score': round(float(row.avg_confidence), 3) if row.avg_confidence else 0.0,
            'time_window_hours': hours
        }
    
    async def get_completion_metrics(
        self, 
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get interview completion behavior metrics for the last N hours
        
        Args:
            hours: Time window in hours (default 24h)
            
        Returns:
            Dictionary with completion metrics:
            - interviews_started: Total started
            - interviews_completed: Total completed
            - completion_rate: % completed vs started
            - early_finish_rate: % finished before max_questions
            - user_requested_rate: % user explicitly requested finish
            - agent_signaled_rate: % agent decided to finish
            - safety_limit_rate: % hit safety limit
            - avg_question_count: Average questions per interview
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Query for started events
        stmt_started = select(
            func.count(MetricEvent.id_event).label('started_count')
        ).where(
            and_(
                MetricEvent.event_type == MetricTypeEnum.interview_started,
                MetricEvent.occurred_at >= cutoff_time
            )
        )
        result_started = await self.db.execute(stmt_started)
        started_count = result_started.scalar() or 0
        
        # Query for completion events
        stmt_completed = select(
            func.count(MetricEvent.id_event).label('completed_count'),
            func.sum(case((MetricEvent.early_finish == True, 1), else_=0)).label('early_finish_count'),
            func.sum(case((MetricEvent.completion_reason == 'user_requested', 1), else_=0)).label('user_requested_count'),
            func.sum(case((MetricEvent.completion_reason == 'agent_signaled', 1), else_=0)).label('agent_signaled_count'),
            func.sum(case((MetricEvent.completion_reason == 'safety_limit', 1), else_=0)).label('safety_limit_count'),
            func.avg(MetricEvent.question_count).label('avg_questions')
        ).where(
            and_(
                MetricEvent.event_type == MetricTypeEnum.interview_completed,
                MetricEvent.occurred_at >= cutoff_time
            )
        )
        result_completed = await self.db.execute(stmt_completed)
        row = result_completed.one()
        
        completed = row.completed_count or 0
        early_finish = row.early_finish_count or 0
        user_requested = row.user_requested_count or 0
        agent_signaled = row.agent_signaled_count or 0
        safety_limit = row.safety_limit_count or 0
        
        return {
            'interviews_started': started_count,
            'interviews_completed': completed,
            'completion_rate': round(completed / started_count, 4) if started_count > 0 else 0.0,
            'early_finish_rate': round(early_finish / completed, 4) if completed > 0 else 0.0,
            'user_requested_rate': round(user_requested / completed, 4) if completed > 0 else 0.0,
            'agent_signaled_rate': round(agent_signaled / completed, 4) if completed > 0 else 0.0,
            'safety_limit_rate': round(safety_limit / completed, 4) if completed > 0 else 0.0,
            'avg_question_count': round(float(row.avg_questions), 1) if row.avg_questions else 0.0,
            'time_window_hours': hours
        }
    
    async def get_detection_percentiles(
        self,
        hours: int = 24
    ) -> Dict[str, float]:
        """
        Calculate latency percentiles (p50, p95, p99) for detection events
        
        Args:
            hours: Time window in hours (default 24h)
            
        Returns:
            Dictionary with percentile values:
            - latency_p50_ms: Median latency
            - latency_p95_ms: 95th percentile
            - latency_p99_ms: 99th percentile
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Fetch all latencies for successful detections (need to calculate percentiles in Python)
        stmt = select(
            MetricEvent.latency_ms
        ).where(
            and_(
                MetricEvent.event_type == MetricTypeEnum.detection_invoked,
                MetricEvent.outcome == MetricOutcomeEnum.success,
                MetricEvent.latency_ms.isnot(None),
                MetricEvent.occurred_at >= cutoff_time
            )
        ).order_by(MetricEvent.latency_ms)
        
        result = await self.db.execute(stmt)
        latencies = [float(row[0]) for row in result.fetchall()]
        
        if not latencies:
            return {
                'latency_p50_ms': 0.0,
                'latency_p95_ms': 0.0,
                'latency_p99_ms': 0.0
            }
        
        # Calculate percentiles
        def percentile(data: list, p: float) -> float:
            if not data:
                return 0.0
            k = (len(data) - 1) * p
            f = int(k)
            c = k - f
            if f + 1 < len(data):
                return data[f] * (1 - c) + data[f + 1] * c
            return data[f]
        
        return {
            'latency_p50_ms': round(percentile(latencies, 0.50), 2),
            'latency_p95_ms': round(percentile(latencies, 0.95), 2),
            'latency_p99_ms': round(percentile(latencies, 0.99), 2)
        }
    
    async def delete_old_events(self, days: int = 90) -> int:
        """
        Delete metric events older than N days (for cleanup/retention policy)
        
        Args:
            days: Age threshold in days (default 90 days)
            
        Returns:
            Number of deleted events
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(MetricEvent).where(MetricEvent.occurred_at < cutoff_time)
        result = await self.db.execute(stmt)
        events_to_delete = result.scalars().all()
        
        count = len(events_to_delete)
        for event in events_to_delete:
            await self.db.delete(event)
        
        await self.db.flush()
        return count
