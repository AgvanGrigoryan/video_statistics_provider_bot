# scripts/load_data.py

"""Load video data from JSON file into PostgreSQL database."""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any

from sqlalchemy import text

from database.engine import async_session_factory, engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_datetime(dt_str: str) -> datetime:
    """
    Parse ISO datetime string to datetime object.
    
    Args:
        dt_str: ISO format datetime string (e.g., "2025-08-19T08:54:35+00:00")
    
    Returns:
        datetime object
    """
    # Remove timezone info if present (PostgreSQL will handle it)
    return datetime.fromisoformat(dt_str.replace('+00:00', ''))


def convert_video_dates(video: dict[str, Any]) -> dict[str, Any]:
    """Convert date strings to datetime objects in video dict."""
    video['video_created_at'] = parse_datetime(video['video_created_at'])
    video['created_at'] = parse_datetime(video['created_at'])
    video['updated_at'] = parse_datetime(video['updated_at'])
    return video


def convert_snapshot_dates(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Convert date strings to datetime objects in snapshot dict."""
    snapshot['created_at'] = parse_datetime(snapshot['created_at'])
    snapshot['updated_at'] = parse_datetime(snapshot['updated_at'])
    return snapshot


async def load_videos_from_json(json_path: str) -> None:
    """
    Load videos and snapshots from JSON into database.
    
    Args:
        json_path: Path to videos.json file
    """
    logger.info(f"Loading data from {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    videos_data = data['videos']
    logger.info(f"Found {len(videos_data)} videos in JSON")
    
    videos_to_insert = []
    all_snapshots = []
    
    for video in videos_data:
        # Extract snapshots before converting video
        snapshots = video.pop('snapshots', [])
        
        # Convert date strings to datetime objects
        video = convert_video_dates(video)
        videos_to_insert.append(video)
        
        # Convert snapshot dates
        for snapshot in snapshots:
            snapshot = convert_snapshot_dates(snapshot)
            all_snapshots.append(snapshot)
    
    logger.info(f"Total snapshots: {len(all_snapshots)}")
    
    async with async_session_factory() as session:
        try:
            logger.info("Inserting videos...")
            batch_size = 100
            
            for i in range(0, len(videos_to_insert), batch_size):
                batch = videos_to_insert[i:i + batch_size]
                
                await session.execute(
                    text("""
                        INSERT INTO videos (
                            id, creator_id, video_created_at,
                            views_count, likes_count, comments_count, reports_count,
                            created_at, updated_at
                        ) VALUES (
                            :id, :creator_id, :video_created_at,
                            :views_count, :likes_count, :comments_count, :reports_count,
                            :created_at, :updated_at
                        )
                        ON CONFLICT (id) DO NOTHING
                    """),
                    batch
                )
                
                logger.info(f"  Inserted {min(i + batch_size, len(videos_to_insert))}/{len(videos_to_insert)} videos")
            
            await session.commit()
            logger.info(f"✅ All videos inserted")
            
            logger.info("Inserting snapshots...")
            
            for i in range(0, len(all_snapshots), batch_size):
                batch = all_snapshots[i:i + batch_size]
                
                await session.execute(
                    text("""
                        INSERT INTO video_snapshots (
                            id, video_id,
                            views_count, likes_count, comments_count, reports_count,
                            delta_views_count, delta_likes_count, 
                            delta_comments_count, delta_reports_count,
                            created_at, updated_at
                        ) VALUES (
                            :id, :video_id,
                            :views_count, :likes_count, :comments_count, :reports_count,
                            :delta_views_count, :delta_likes_count,
                            :delta_comments_count, :delta_reports_count,
                            :created_at, :updated_at
                        )
                        ON CONFLICT (id) DO NOTHING
                    """),
                    batch
                )
                
                logger.info(f"  Inserted {min(i + batch_size, len(all_snapshots))}/{len(all_snapshots)} snapshots")
            
            await session.commit()
            
            logger.info(
                f"✅ Successfully loaded:\n"
                f"   - {len(videos_to_insert)} videos\n"
                f"   - {len(all_snapshots)} snapshots"
            )
            
        except Exception as e:
            logger.exception(f"Error loading data: {e}")
            await session.rollback()
            raise


async def main():
    """Main entry point."""
    json_path = Path(__file__).parent.parent / "videos.json"
    
    if not json_path.exists():
        logger.error(f"File not found: {json_path}")
        return
    
    start_time = datetime.now()
    await load_videos_from_json(str(json_path))
    elapsed = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"⏱️  Total time: {elapsed:.2f} seconds")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())