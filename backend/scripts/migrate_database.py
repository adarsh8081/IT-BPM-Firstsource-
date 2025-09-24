"""
Script to run database migrations
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from database import init_db
from config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Run database migrations"""
    try:
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
