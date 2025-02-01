import json
import os
import logging
from typing import List

class ParserService:
    def __init__(self, client, data_dir: str, config: dict):
        self.client = client
        self.data_dir = data_dir
        self.config = config

    async def parse_channel(self, channel_username: str) -> List[str]:
        try:
            max_messages = self.config.get("max_messages_per_parse", 1000)
            logging.info(f"Starting to parse {channel_username}, max messages: {max_messages}")

            messages = await self.client.get_messages(
                channel_username,
                limit=max_messages
            )

            # Get all messages with text
            parsed_messages = [msg.text for msg in messages if msg.text]

            total_messages = len(messages)
            text_messages = len(parsed_messages)
            skipped_messages = total_messages - text_messages

            logging.info(
                f"Channel {channel_username} statistics:\n"
                f"- Total messages fetched: {total_messages}\n"
                f"- Messages with text: {text_messages}\n"
                f"- Skipped (no text): {skipped_messages}"
            )

            os.makedirs(self.data_dir, exist_ok=True)
            file_path = os.path.join(self.data_dir, f"{channel_username}_posts.json")

            with open(file_path, "w", encoding="utf-8") as json_file:
                json.dump(parsed_messages, json_file, ensure_ascii=False, indent=4)

            return parsed_messages

        except Exception as e:
            logging.error(f"Error parsing channel: {e}")
            raise