import json
import os
import logging
from datetime import datetime
from pathlib import Path
from personality_analyzer import Personality

logger = logging.getLogger(__name__)

class LogService:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.logs_dir = os.path.join(base_dir, "logs", "personalities")
        os.makedirs(self.logs_dir, exist_ok=True)
        logger.info(f"Initialized LogService with logs directory: {self.logs_dir}")

    def save_personality(self, channel_username: str, personality: Personality) -> None:
        """Save personality analysis to a log file"""
        try:
            # Remove @ if present
            clean_username = channel_username[1:] if channel_username.startswith('@') else channel_username

            # Create timestamp for the filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"{clean_username}_{timestamp}.json"
            filepath = os.path.join(self.logs_dir, filename)

            # Prepare data for saving
            data = {
                "channel": clean_username,
                "timestamp": datetime.utcnow().isoformat(),
                "personality": {
                    "name": personality.name,
                    "traits": personality.traits,
                    "interests": personality.interests,
                    "communication_style": personality.communication_style,
                    "created_at": personality.created_at,
                    "updated_at": personality.updated_at,
                    "post_count": personality.post_count,
                    "raw_analysis": personality.raw_analysis
                }
            }

            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved personality analysis for {channel_username} to {filepath}")

        except Exception as e:
            logger.error(f"Error saving personality analysis for {channel_username}: {e}", exc_info=True)