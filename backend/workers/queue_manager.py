"""
Job Queue Manager

This module manages Redis Queue (RQ) workers and job processing for the validation system.
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import redis
from rq import Queue, Worker, Connection
from rq.job import Job
from rq.exceptions import NoSuchJobError
import multiprocessing

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Queue Manager for Redis Queue (RQ)
    
    Manages job queues, workers, and job processing for the validation system.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize Queue Manager
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis_conn = redis.from_url(redis_url)
        
        # Initialize job queues
        self.queues = {
            'npi_validation': Queue('npi_validation', connection=self.redis_conn),
            'google_places_validation': Queue('google_places_validation', connection=self.redis_conn),
            'ocr_processing': Queue('ocr_processing', connection=self.redis_conn),
            'state_board_validation': Queue('state_board_validation', connection=self.redis_conn),
            'enrichment_lookup': Queue('enrichment_lookup', connection=self.redis_conn)
        }
        
        # Worker processes
        self.workers = {}
        self.worker_processes = {}
        
        # Queue configuration
        self.queue_config = {
            'npi_validation': {
                'worker_count': 2,
                'timeout': 300,  # 5 minutes
                'retry_count': 3
            },
            'google_places_validation': {
                'worker_count': 2,
                'timeout': 300,  # 5 minutes
                'retry_count': 3
            },
            'ocr_processing': {
                'worker_count': 1,  # OCR is CPU intensive
                'timeout': 600,  # 10 minutes
                'retry_count': 2
            },
            'state_board_validation': {
                'worker_count': 1,  # Rate limited
                'timeout': 300,  # 5 minutes
                'retry_count': 3
            },
            'enrichment_lookup': {
                'worker_count': 2,
                'timeout': 300,  # 5 minutes
                'retry_count': 3
            }
        }
    
    def start_workers(self):
        """Start all worker processes"""
        try:
            for queue_name, queue in self.queues.items():
                config = self.queue_config[queue_name]
                worker_count = config['worker_count']
                
                logger.info(f"Starting {worker_count} workers for {queue_name}")
                
                for i in range(worker_count):
                    worker_name = f"{queue_name}_worker_{i}"
                    worker = Worker([queue], connection=self.redis_conn, name=worker_name)
                    
                    # Start worker in separate process
                    process = multiprocessing.Process(
                        target=self._run_worker,
                        args=(worker_name, queue_name, config),
                        daemon=True
                    )
                    
                    process.start()
                    self.worker_processes[worker_name] = process
                    
                    logger.info(f"Started worker {worker_name} (PID: {process.pid})")
            
            logger.info("All workers started successfully")
        
        except Exception as e:
            logger.error(f"Failed to start workers: {str(e)}")
            raise
    
    def stop_workers(self):
        """Stop all worker processes"""
        try:
            for worker_name, process in self.worker_processes.items():
                if process.is_alive():
                    logger.info(f"Stopping worker {worker_name} (PID: {process.pid})")
                    process.terminate()
                    process.join(timeout=10)
                    
                    if process.is_alive():
                        logger.warning(f"Force killing worker {worker_name}")
                        process.kill()
                        process.join()
            
            self.worker_processes.clear()
            logger.info("All workers stopped")
        
        except Exception as e:
            logger.error(f"Failed to stop workers: {str(e)}")
            raise
    
    def _run_worker(self, worker_name: str, queue_name: str, config: Dict[str, Any]):
        """
        Run worker process
        
        Args:
            worker_name: Worker name
            queue_name: Queue name
            config: Worker configuration
        """
        try:
            # Set up logging for worker process
            logging.basicConfig(
                level=logging.INFO,
                format=f'%(asctime)s - {worker_name} - %(levelname)s - %(message)s'
            )
            
            # Create worker
            queue = Queue(queue_name, connection=self.redis_conn)
            worker = Worker([queue], connection=self.redis_conn, name=worker_name)
            
            # Set up signal handlers
            signal.signal(signal.SIGTERM, lambda sig, frame: worker.stop())
            signal.signal(signal.SIGINT, lambda sig, frame: worker.stop())
            
            logger.info(f"Worker {worker_name} started")
            
            # Start working
            worker.work(
                with_scheduler=True,
                logging_level='INFO'
            )
        
        except Exception as e:
            logger.error(f"Worker {worker_name} failed: {str(e)}")
            raise
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get status of all queues
        
        Returns:
            Queue status information
        """
        try:
            status = {}
            
            for queue_name, queue in self.queues.items():
                status[queue_name] = {
                    'length': len(queue),
                    'failed_jobs': len(queue.failed_job_registry),
                    'finished_jobs': len(queue.finished_job_registry),
                    'started_jobs': len(queue.started_job_registry),
                    'scheduled_jobs': len(queue.scheduled_job_registry)
                }
            
            return status
        
        except Exception as e:
            logger.error(f"Failed to get queue status: {str(e)}")
            return {}
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status
        
        Args:
            job_id: Job ID
            
        Returns:
            Job status information
        """
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            
            return {
                'job_id': job.id,
                'status': job.get_status(),
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'ended_at': job.ended_at.isoformat() if job.ended_at else None,
                'result': job.result,
                'exc_info': job.exc_info,
                'meta': job.meta,
                'timeout': job.timeout,
                'retry_count': job.retry_count
            }
        
        except NoSuchJobError:
            return None
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {str(e)}")
            return None
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job
        
        Args:
            job_id: Job ID
            
        Returns:
            True if job was cancelled, False otherwise
        """
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            job.cancel()
            
            logger.info(f"Cancelled job {job_id}")
            return True
        
        except NoSuchJobError:
            logger.warning(f"Job {job_id} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {str(e)}")
            return False
    
    def retry_failed_jobs(self, queue_name: str, limit: int = 10) -> int:
        """
        Retry failed jobs in a queue
        
        Args:
            queue_name: Queue name
            limit: Maximum number of jobs to retry
            
        Returns:
            Number of jobs retried
        """
        try:
            queue = self.queues[queue_name]
            failed_jobs = queue.failed_job_registry.get_job_ids()
            
            retried_count = 0
            for job_id in failed_jobs[:limit]:
                try:
                    job = Job.fetch(job_id, connection=self.redis_conn)
                    job.retry()
                    retried_count += 1
                    logger.info(f"Retried failed job {job_id}")
                except Exception as e:
                    logger.error(f"Failed to retry job {job_id}: {str(e)}")
            
            logger.info(f"Retried {retried_count} failed jobs in {queue_name}")
            return retried_count
        
        except Exception as e:
            logger.error(f"Failed to retry failed jobs in {queue_name}: {str(e)}")
            return 0
    
    def cleanup_old_jobs(self, days: int = 7):
        """
        Clean up old finished jobs
        
        Args:
            days: Number of days to keep jobs
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for queue_name, queue in self.queues.items():
                # Clean up finished jobs
                finished_jobs = queue.finished_job_registry.get_job_ids()
                cleaned_count = 0
                
                for job_id in finished_jobs:
                    try:
                        job = Job.fetch(job_id, connection=self.redis_conn)
                        if job.ended_at and job.ended_at < cutoff_date:
                            job.delete()
                            cleaned_count += 1
                    except Exception as e:
                        logger.error(f"Failed to clean up job {job_id}: {str(e)}")
                
                logger.info(f"Cleaned up {cleaned_count} old jobs from {queue_name}")
        
        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {str(e)}")
    
    def get_worker_status(self) -> Dict[str, Any]:
        """
        Get status of all workers
        
        Returns:
            Worker status information
        """
        try:
            status = {}
            
            for worker_name, process in self.worker_processes.items():
                status[worker_name] = {
                    'pid': process.pid,
                    'alive': process.is_alive(),
                    'exitcode': process.exitcode
                }
            
            return status
        
        except Exception as e:
            logger.error(f"Failed to get worker status: {str(e)}")
            return {}
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on queues and workers
        
        Returns:
            Health check results
        """
        try:
            # Check Redis connection
            self.redis_conn.ping()
            
            # Check queue status
            queue_status = self.get_queue_status()
            
            # Check worker status
            worker_status = self.get_worker_status()
            
            # Determine overall health
            healthy_workers = sum(1 for w in worker_status.values() if w['alive'])
            total_workers = len(worker_status)
            
            overall_health = "healthy" if healthy_workers == total_workers else "degraded"
            
            return {
                'status': overall_health,
                'redis_connection': 'healthy',
                'queue_status': queue_status,
                'worker_status': worker_status,
                'healthy_workers': healthy_workers,
                'total_workers': total_workers,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Global queue manager instance
queue_manager = QueueManager()


# Command line interface for managing workers

def start_workers_command():
    """Command to start workers"""
    try:
        logging.basicConfig(level=logging.INFO)
        queue_manager.start_workers()
        
        # Keep running until interrupted
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down workers...")
            queue_manager.stop_workers()
    
    except Exception as e:
        logger.error(f"Failed to start workers: {str(e)}")
        sys.exit(1)


def stop_workers_command():
    """Command to stop workers"""
    try:
        logging.basicConfig(level=logging.INFO)
        queue_manager.stop_workers()
        logger.info("Workers stopped")
    
    except Exception as e:
        logger.error(f"Failed to stop workers: {str(e)}")
        sys.exit(1)


def status_command():
    """Command to show status"""
    try:
        logging.basicConfig(level=logging.INFO)
        
        # Health check
        health = queue_manager.health_check()
        print(f"Overall Status: {health['status']}")
        print(f"Healthy Workers: {health['healthy_workers']}/{health['total_workers']}")
        
        # Queue status
        queue_status = queue_manager.get_queue_status()
        print("\nQueue Status:")
        for queue_name, status in queue_status.items():
            print(f"  {queue_name}: {status['length']} jobs")
        
        # Worker status
        worker_status = queue_manager.get_worker_status()
        print("\nWorker Status:")
        for worker_name, status in worker_status.items():
            print(f"  {worker_name}: {'Running' if status['alive'] else 'Stopped'} (PID: {status['pid']})")
    
    except Exception as e:
        logger.error(f"Failed to get status: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Queue Manager CLI")
    parser.add_argument("command", choices=["start", "stop", "status"], help="Command to run")
    
    args = parser.parse_args()
    
    if args.command == "start":
        start_workers_command()
    elif args.command == "stop":
        stop_workers_command()
    elif args.command == "status":
        status_command()