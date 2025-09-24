"""
Script to run the validation worker
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from workers.validation_worker import ValidationWorker
from config import settings

def setup_logging():
    """Set up logging configuration"""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('worker.log')
        ]
    )

async def main():
    """Main function to start the worker"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting validation worker...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Redis URL: {settings.REDIS_URL}")
    
    worker = ValidationWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker error: {e}")
        raise
    finally:
        logger.info("Validation worker stopped")

if __name__ == "__main__":
    asyncio.run(main())
