"""
Validation worker for processing validation jobs
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, Any
import redis
from rq import Worker, Queue, Connection
from rq.job import Job

from ..database import AsyncSessionLocal, init_db
from ..services import ValidationService
from ..config import settings

logger = logging.getLogger(__name__)

class ValidationWorker:
    """Worker for processing validation jobs"""
    
    def __init__(self):
        self.redis_conn = redis.from_url(settings.REDIS_URL)
        self.queue = Queue('validation', connection=self.redis_conn)
        self.running = False
        
    async def start(self):
        """Start the validation worker"""
        logger.info("Starting validation worker...")
        
        # Initialize database
        await init_db()
        
        self.running = True
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Start worker
        try:
            with Connection(self.redis_conn):
                worker = Worker(['validation'])
                worker.work(with_scheduler=True)
        except KeyboardInterrupt:
            logger.info("Worker interrupted by user")
        except Exception as e:
            logger.error(f"Worker error: {e}")
        finally:
            self.running = False
            logger.info("Validation worker stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        sys.exit(0)

def process_validation_job(job_id: str) -> Dict[str, Any]:
    """Process a single validation job"""
    try:
        logger.info(f"Processing validation job {job_id}")
        
        # Create database session
        async def _process():
            async with AsyncSessionLocal() as db:
                validation_service = ValidationService(db)
                await validation_service.process_validation_job(job_id)
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_process())
            return {"success": True, "job_id": job_id}
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Failed to process validation job {job_id}: {e}")
        return {"success": False, "job_id": job_id, "error": str(e)}

def enqueue_validation_job(job_id: str, priority: str = 'normal') -> Dict[str, Any]:
    """Enqueue a validation job"""
    try:
        redis_conn = redis.from_url(settings.REDIS_URL)
        queue = Queue('validation', connection=redis_conn)
        
        job = queue.enqueue(
            process_validation_job,
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
            "status": "queued"
        }
        
    except Exception as e:
        logger.error(f"Failed to enqueue validation job {job_id}: {e}")
        return {
            "success": False,
            "job_id": job_id,
            "error": str(e)
        }

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Start worker
    worker = ValidationWorker()
    asyncio.run(worker.start())
