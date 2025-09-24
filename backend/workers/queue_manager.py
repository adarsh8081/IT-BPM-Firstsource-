"""
Queue manager for handling validation job queues
"""

import asyncio
import logging
import redis
from rq import Queue, Worker, Connection
from rq.job import Job
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ..config import settings

logger = logging.getLogger(__name__)

class QueueManager:
    """Manager for validation job queues"""
    
    def __init__(self):
        self.redis_conn = redis.from_url(settings.REDIS_URL)
        self.queue = Queue('validation', connection=self.redis_conn)
    
    def enqueue_job(self, job_id: str, priority: str = 'normal') -> Dict[str, Any]:
        """Enqueue a validation job"""
        try:
            job = self.queue.enqueue(
                'workers.validation_worker.process_validation_job',
                job_id,
                job_timeout='30m',
                retry=True,
                job_id=f"validation_{job_id}"
            )
            
            logger.info(f"Enqueued validation job {job_id} with RQ job {job.id}")
            return {
                "success": True,
                "job_id": job_id,
                "rq_job_id": job.id,
                "status": "queued",
                "created_at": job.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to enqueue validation job {job_id}: {e}")
            return {
                "success": False,
                "job_id": job_id,
                "error": str(e)
            }
    
    def get_job_status(self, rq_job_id: str) -> Dict[str, Any]:
        """Get status of a queued job"""
        try:
            job = Job.fetch(rq_job_id, connection=self.redis_conn)
            
            return {
                "success": True,
                "rq_job_id": rq_job_id,
                "status": job.get_status(),
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
                "result": job.result,
                "exc_info": job.exc_info,
                "progress": job.meta.get('progress', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get job status for {rq_job_id}: {e}")
            return {
                "success": False,
                "rq_job_id": rq_job_id,
                "error": str(e)
            }
    
    def cancel_job(self, rq_job_id: str) -> Dict[str, Any]:
        """Cancel a queued job"""
        try:
            job = Job.fetch(rq_job_id, connection=self.redis_conn)
            job.cancel()
            
            logger.info(f"Cancelled job {rq_job_id}")
            return {
                "success": True,
                "rq_job_id": rq_job_id,
                "status": "cancelled"
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel job {rq_job_id}: {e}")
            return {
                "success": False,
                "rq_job_id": rq_job_id,
                "error": str(e)
            }
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get overall queue status"""
        try:
            # Get queue statistics
            queue_length = len(self.queue)
            failed_jobs = self.queue.failed_job_registry.count
            scheduled_jobs = self.queue.scheduled_job_registry.count
            started_jobs = self.queue.started_job_registry.count
            
            # Get worker information
            workers = Worker.all(connection=self.redis_conn)
            worker_info = []
            
            for worker in workers:
                worker_info.append({
                    "name": worker.name,
                    "state": worker.get_state(),
                    "current_job": worker.get_current_job_id(),
                    "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None
                })
            
            return {
                "success": True,
                "queue_name": self.queue.name,
                "queue_length": queue_length,
                "failed_jobs": failed_jobs,
                "scheduled_jobs": scheduled_jobs,
                "started_jobs": started_jobs,
                "workers": worker_info,
                "worker_count": len(workers)
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_recent_jobs(self, limit: int = 10) -> Dict[str, Any]:
        """Get recent jobs from the queue"""
        try:
            # Get recent jobs
            recent_jobs = []
            
            # Get finished jobs
            finished_jobs = self.queue.finished_job_registry.get_job_ids()
            for job_id in finished_jobs[-limit:]:
                try:
                    job = Job.fetch(job_id, connection=self.redis_conn)
                    recent_jobs.append({
                        "rq_job_id": job.id,
                        "status": job.get_status(),
                        "created_at": job.created_at.isoformat() if job.created_at else None,
                        "ended_at": job.ended_at.isoformat() if job.ended_at else None,
                        "result": job.result
                    })
                except Exception:
                    continue
            
            # Get failed jobs
            failed_jobs = self.queue.failed_job_registry.get_job_ids()
            for job_id in failed_jobs[-limit:]:
                try:
                    job = Job.fetch(job_id, connection=self.redis_conn)
                    recent_jobs.append({
                        "rq_job_id": job.id,
                        "status": job.get_status(),
                        "created_at": job.created_at.isoformat() if job.created_at else None,
                        "ended_at": job.ended_at.isoformat() if job.ended_at else None,
                        "exc_info": job.exc_info
                    })
                except Exception:
                    continue
            
            # Sort by creation time
            recent_jobs.sort(key=lambda x: x['created_at'] or '', reverse=True)
            
            return {
                "success": True,
                "jobs": recent_jobs[:limit],
                "count": len(recent_jobs[:limit])
            }
            
        except Exception as e:
            logger.error(f"Failed to get recent jobs: {e}")
            return {
                "success": False,
                "error": str(e),
                "jobs": []
            }
    
    def retry_failed_jobs(self, job_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Retry failed jobs"""
        try:
            retried_count = 0
            
            if job_ids:
                # Retry specific jobs
                for job_id in job_ids:
                    try:
                        job = Job.fetch(job_id, connection=self.redis_conn)
                        if job.get_status() == 'failed':
                            job.retry()
                            retried_count += 1
                    except Exception as e:
                        logger.error(f"Failed to retry job {job_id}: {e}")
            else:
                # Retry all failed jobs
                failed_jobs = self.queue.failed_job_registry.get_job_ids()
                for job_id in failed_jobs:
                    try:
                        job = Job.fetch(job_id, connection=self.redis_conn)
                        job.retry()
                        retried_count += 1
                    except Exception as e:
                        logger.error(f"Failed to retry job {job_id}: {e}")
            
            logger.info(f"Retried {retried_count} failed jobs")
            return {
                "success": True,
                "retried_count": retried_count
            }
            
        except Exception as e:
            logger.error(f"Failed to retry failed jobs: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def clear_failed_jobs(self) -> Dict[str, Any]:
        """Clear all failed jobs from the registry"""
        try:
            failed_count = self.queue.failed_job_registry.count
            self.queue.failed_job_registry.clear()
            
            logger.info(f"Cleared {failed_count} failed jobs")
            return {
                "success": True,
                "cleared_count": failed_count
            }
            
        except Exception as e:
            logger.error(f"Failed to clear failed jobs: {e}")
            return {
                "success": False,
                "error": str(e)
            }
