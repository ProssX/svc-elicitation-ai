"""
Metrics Service
Collects and tracks metrics for monitoring interview performance

This service uses a dual-write pattern:
- In-memory: Fast aggregations for real-time monitoring (deque, counters)
- PostgreSQL: Historical persistence for trend analysis and reporting
"""
import time
from typing import Dict, List, Optional
from uuid import UUID
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging
import asyncio

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects metrics for monitoring interview and process detection performance
    
    Metrics tracked:
    - Process detection invocation rate
    - Process detection latency (p50, p95, p99)
    - Process detection timeout rate
    - Process detection error rate
    - Confidence score distribution
    - Dynamic completion early finish rate
    """
    
    def __init__(self, window_size: int = 1000):
        """
        Initialize metrics collector
        
        Args:
            window_size: Number of recent samples to keep for percentile calculations
        """
        self.window_size = window_size
        
        # Detection metrics
        self.detection_invocations = 0
        self.detection_successes = 0
        self.detection_timeouts = 0
        self.detection_errors = 0
        self.detection_latencies = deque(maxlen=window_size)  # milliseconds
        self.confidence_scores = deque(maxlen=window_size)  # 0.0 to 1.0
        
        # Interview completion metrics
        self.interviews_started = 0
        self.interviews_completed = 0
        self.early_completions = 0  # Finished before max_questions
        self.user_requested_completions = 0  # User explicitly asked to finish
        self.agent_signaled_completions = 0  # Agent signaled completion
        self.safety_limit_completions = 0  # Hit safety limit
        
        # Question count distribution
        self.question_counts = deque(maxlen=window_size)
        
        # Timestamps for rate calculations
        self.detection_timestamps = deque(maxlen=window_size)
        self.completion_timestamps = deque(maxlen=window_size)
        
        # Start time for uptime tracking
        self.start_time = datetime.now()
    
    def record_detection_invocation(
        self,
        latency_ms: float,
        success: bool,
        timeout: bool = False,
        error: bool = False,
        confidence_score: Optional[float] = None
    ):
        """
        Record a process detection invocation
        
        Args:
            latency_ms: Detection latency in milliseconds
            success: Whether detection completed successfully
            timeout: Whether detection timed out
            error: Whether detection encountered an error
            confidence_score: Confidence score if detection succeeded
        """
        # In-memory tracking (fast)
        self.detection_invocations += 1
        self.detection_timestamps.append(time.time())
        
        if success:
            self.detection_successes += 1
            self.detection_latencies.append(latency_ms)
            
            if confidence_score is not None:
                self.confidence_scores.append(confidence_score)
        
        if timeout:
            self.detection_timeouts += 1
        
        if error:
            self.detection_errors += 1
        
        logger.info(
            "[METRICS] Detection recorded",
            extra={
                "latency_ms": latency_ms,
                "success": success,
                "timeout": timeout,
                "error": error,
                "confidence_score": confidence_score,
                "total_invocations": self.detection_invocations
            }
        )
        
        # Persist to database (async, fire-and-forget)
        asyncio.create_task(self._persist_detection_event(
            latency_ms=latency_ms,
            success=success,
            timeout=timeout,
            error=error,
            confidence_score=confidence_score
        ))
    
    def record_interview_start(
        self, 
        interview_id: Optional[UUID] = None,
        employee_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        language: Optional[str] = None
    ):
        """
        Record an interview start
        
        Args:
            interview_id: Optional interview UUID for linking event to interview
            employee_id: Employee who started the interview
            organization_id: Organization context
            language: Interview language (es/en/pt)
        """
        # In-memory tracking (fast)
        self.interviews_started += 1
        
        logger.info(
            "[METRICS] Interview started",
            extra={
                "total_started": self.interviews_started, 
                "interview_id": str(interview_id) if interview_id else None,
                "employee_id": str(employee_id) if employee_id else None,
                "organization_id": str(organization_id) if organization_id else None,
                "language": language
            }
        )
        
        # Persist to database (async, fire-and-forget)
        asyncio.create_task(self._persist_interview_start_event(
            interview_id=interview_id,
            employee_id=employee_id,
            organization_id=organization_id,
            language=language
        ))
    
    def record_interview_completion(
        self,
        question_count: int,
        early_finish: bool = False,
        user_requested: bool = False,
        agent_signaled: bool = False,
        safety_limit: bool = False,
        interview_id: Optional[UUID] = None,
        employee_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        language: Optional[str] = None
    ):
        """
        Record an interview completion
        
        Args:
            question_count: Number of questions asked
            early_finish: Whether interview finished before max_questions
            user_requested: Whether user explicitly requested to finish
            agent_signaled: Whether agent signaled completion
            safety_limit: Whether safety limit was reached
            interview_id: Optional interview UUID for linking event to interview
        """
        # In-memory tracking (fast)
        self.interviews_completed += 1
        self.completion_timestamps.append(time.time())
        self.question_counts.append(question_count)
        
        if early_finish:
            self.early_completions += 1
        
        if user_requested:
            self.user_requested_completions += 1
        
        if agent_signaled:
            self.agent_signaled_completions += 1
        
        if safety_limit:
            self.safety_limit_completions += 1
        
        # Determine completion reason
        completion_reason = None
        if user_requested:
            completion_reason = "user_requested"
        elif agent_signaled:
            completion_reason = "agent_signaled"
        elif safety_limit:
            completion_reason = "safety_limit"
        else:
            completion_reason = "max_questions"
        
        logger.info(
            "[METRICS] Interview completed",
            extra={
                "question_count": question_count,
                "early_finish": early_finish,
                "user_requested": user_requested,
                "agent_signaled": agent_signaled,
                "safety_limit": safety_limit,
                "completion_reason": completion_reason,
                "total_completed": self.interviews_completed,
                "interview_id": str(interview_id) if interview_id else None,
                "employee_id": str(employee_id) if employee_id else None,
                "organization_id": str(organization_id) if organization_id else None,
                "language": language
            }
        )
        
        # Persist to database (async, fire-and-forget)
        asyncio.create_task(self._persist_interview_completion_event(
            interview_id=interview_id,
            question_count=question_count,
            early_finish=early_finish,
            completion_reason=completion_reason,
            employee_id=employee_id,
            organization_id=organization_id,
            language=language
        ))
    
    def get_detection_metrics(self) -> Dict:
        """
        Get current detection metrics
        
        Returns:
            Dict with detection metrics
        """
        total = self.detection_invocations
        
        if total == 0:
            return {
                "invocation_count": 0,
                "success_rate": 0.0,
                "timeout_rate": 0.0,
                "error_rate": 0.0,
                "latency_p50_ms": 0.0,
                "latency_p95_ms": 0.0,
                "latency_p99_ms": 0.0,
                "avg_confidence_score": 0.0,
                "invocation_rate_per_minute": 0.0
            }
        
        # Calculate rates
        success_rate = self.detection_successes / total
        timeout_rate = self.detection_timeouts / total
        error_rate = self.detection_errors / total
        
        # Calculate latency percentiles
        latencies = sorted(self.detection_latencies)
        p50 = self._percentile(latencies, 50) if latencies else 0.0
        p95 = self._percentile(latencies, 95) if latencies else 0.0
        p99 = self._percentile(latencies, 99) if latencies else 0.0
        
        # Calculate average confidence score
        avg_confidence = (
            sum(self.confidence_scores) / len(self.confidence_scores)
            if self.confidence_scores else 0.0
        )
        
        # Calculate invocation rate (per minute)
        invocation_rate = self._calculate_rate(self.detection_timestamps)
        
        return {
            "invocation_count": total,
            "success_rate": round(success_rate, 4),
            "timeout_rate": round(timeout_rate, 4),
            "error_rate": round(error_rate, 4),
            "latency_p50_ms": round(p50, 2),
            "latency_p95_ms": round(p95, 2),
            "latency_p99_ms": round(p99, 2),
            "avg_confidence_score": round(avg_confidence, 4),
            "invocation_rate_per_minute": round(invocation_rate, 2)
        }
    
    def get_completion_metrics(self) -> Dict:
        """
        Get current interview completion metrics
        
        Returns:
            Dict with completion metrics
        """
        total_completed = self.interviews_completed
        
        if total_completed == 0:
            return {
                "interviews_started": self.interviews_started,
                "interviews_completed": 0,
                "completion_rate": 0.0,
                "early_finish_rate": 0.0,
                "user_requested_rate": 0.0,
                "agent_signaled_rate": 0.0,
                "safety_limit_rate": 0.0,
                "avg_question_count": 0.0,
                "completion_rate_per_minute": 0.0
            }
        
        # Calculate rates
        completion_rate = total_completed / self.interviews_started if self.interviews_started > 0 else 0.0
        early_finish_rate = self.early_completions / total_completed
        user_requested_rate = self.user_requested_completions / total_completed
        agent_signaled_rate = self.agent_signaled_completions / total_completed
        safety_limit_rate = self.safety_limit_completions / total_completed
        
        # Calculate average question count
        avg_questions = (
            sum(self.question_counts) / len(self.question_counts)
            if self.question_counts else 0.0
        )
        
        # Calculate completion rate (per minute)
        completion_rate_per_min = self._calculate_rate(self.completion_timestamps)
        
        return {
            "interviews_started": self.interviews_started,
            "interviews_completed": total_completed,
            "completion_rate": round(completion_rate, 4),
            "early_finish_rate": round(early_finish_rate, 4),
            "user_requested_rate": round(user_requested_rate, 4),
            "agent_signaled_rate": round(agent_signaled_rate, 4),
            "safety_limit_rate": round(safety_limit_rate, 4),
            "avg_question_count": round(avg_questions, 2),
            "completion_rate_per_minute": round(completion_rate_per_min, 2)
        }
    
    def get_all_metrics(self) -> Dict:
        """
        Get all metrics
        
        Returns:
            Dict with all metrics
        """
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "uptime_seconds": round(uptime_seconds, 2),
            "uptime_hours": round(uptime_seconds / 3600, 2),
            "detection": self.get_detection_metrics(),
            "completion": self.get_completion_metrics()
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """
        Calculate percentile of a sorted list
        
        Args:
            data: Sorted list of values
            percentile: Percentile to calculate (0-100)
            
        Returns:
            Percentile value
        """
        if not data:
            return 0.0
        
        k = (len(data) - 1) * (percentile / 100.0)
        f = int(k)
        c = f + 1
        
        if c >= len(data):
            return data[-1]
        
        d0 = data[f] * (c - k)
        d1 = data[c] * (k - f)
        
        return d0 + d1
    
    def _calculate_rate(self, timestamps: deque) -> float:
        """
        Calculate rate per minute from timestamps
        
        Args:
            timestamps: Deque of timestamps (seconds since epoch)
            
        Returns:
            Rate per minute
        """
        if len(timestamps) < 2:
            return 0.0
        
        # Calculate rate over last minute
        now = time.time()
        one_minute_ago = now - 60
        
        recent_count = sum(1 for ts in timestamps if ts >= one_minute_ago)
        
        return recent_count
    
    async def _persist_detection_event(
        self,
        latency_ms: float,
        success: bool,
        timeout: bool,
        error: bool,
        confidence_score: Optional[float]
    ):
        """
        Persist detection event to database (async)
        
        Uses fire-and-forget pattern - failures are logged but don't block the caller
        """
        try:
            from app.database import AsyncSessionLocal
            from app.models.db_models import MetricEvent, MetricTypeEnum, MetricOutcomeEnum
            
            # Determine outcome
            if success:
                outcome = MetricOutcomeEnum.success
            elif timeout:
                outcome = MetricOutcomeEnum.timeout
            elif error:
                outcome = MetricOutcomeEnum.error
            else:
                outcome = MetricOutcomeEnum.not_applicable
            
            async with AsyncSessionLocal() as db:
                event = MetricEvent(
                    event_type=MetricTypeEnum.detection_invoked,
                    outcome=outcome,
                    interview_id=None,  # Detection events aren't linked to specific interviews
                    latency_ms=latency_ms,
                    confidence_score=confidence_score if success else None,
                    question_count=None,
                    early_finish=None,
                    completion_reason=None,
                    occurred_at=datetime.utcnow()
                )
                db.add(event)
                await db.commit()
                
        except Exception as e:
            logger.error(f"[METRICS] Failed to persist detection event to DB: {e}", exc_info=True)
    
    async def _persist_interview_start_event(
        self, 
        interview_id: Optional[UUID],
        employee_id: Optional[UUID],
        organization_id: Optional[UUID],
        language: Optional[str]
    ):
        """
        Persist interview start event to database (async)
        
        Uses fire-and-forget pattern - failures are logged but don't block the caller
        """
        try:
            from app.database import AsyncSessionLocal
            from app.models.db_models import MetricEvent, MetricTypeEnum, MetricOutcomeEnum
            
            async with AsyncSessionLocal() as db:
                event = MetricEvent(
                    event_type=MetricTypeEnum.interview_started,
                    outcome=MetricOutcomeEnum.not_applicable,
                    interview_id=interview_id,
                    employee_id=employee_id,
                    organization_id=organization_id,
                    language=language,
                    latency_ms=None,
                    confidence_score=None,
                    question_count=None,
                    early_finish=None,
                    completion_reason=None,
                    occurred_at=datetime.utcnow()
                )
                db.add(event)
                await db.commit()
                
        except Exception as e:
            logger.error(f"[METRICS] Failed to persist interview start event to DB: {e}", exc_info=True)
    
    async def _persist_interview_completion_event(
        self,
        interview_id: Optional[UUID],
        question_count: int,
        early_finish: bool,
        completion_reason: str,
        employee_id: Optional[UUID],
        organization_id: Optional[UUID],
        language: Optional[str]
    ):
        """
        Persist interview completion event to database (async)
        
        Uses fire-and-forget pattern - failures are logged but don't block the caller
        """
        try:
            from app.database import AsyncSessionLocal
            from app.models.db_models import MetricEvent, MetricTypeEnum, MetricOutcomeEnum
            
            async with AsyncSessionLocal() as db:
                event = MetricEvent(
                    event_type=MetricTypeEnum.interview_completed,
                    outcome=MetricOutcomeEnum.not_applicable,
                    interview_id=interview_id,
                    employee_id=employee_id,
                    organization_id=organization_id,
                    language=language,
                    latency_ms=None,
                    confidence_score=None,
                    question_count=question_count,
                    early_finish=early_finish,
                    completion_reason=completion_reason,
                    occurred_at=datetime.utcnow()
                )
                db.add(event)
                await db.commit()
                
        except Exception as e:
            logger.error(f"[METRICS] Failed to persist interview completion event to DB: {e}", exc_info=True)
    
    def reset(self):
        """Reset all metrics"""
        self.detection_invocations = 0
        self.detection_successes = 0
        self.detection_timeouts = 0
        self.detection_errors = 0
        self.detection_latencies.clear()
        self.confidence_scores.clear()
        
        self.interviews_started = 0
        self.interviews_completed = 0
        self.early_completions = 0
        self.user_requested_completions = 0
        self.agent_signaled_completions = 0
        self.safety_limit_completions = 0
        
        self.question_counts.clear()
        self.detection_timestamps.clear()
        self.completion_timestamps.clear()
        
        self.start_time = datetime.now()
        
        logger.info("[METRICS] All metrics reset")


# Global metrics collector instance
_metrics_collector = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
