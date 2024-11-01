from typing import Dict
import os
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageServer:
    def __init__(self, message_file: str = "messages.json"):
        self.message_file = message_file
        self.messages: Dict = self._load_all_messages()

    def _load_all_messages(self) -> Dict:
        """Load all messages from a JSON file."""
        if os.path.exists(self.message_file):
            try:
                with open(self.message_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Error: Invalid JSON format in {self.message_file}")
                return {}
            except Exception as e:
                logger.error(f"Error loading messages: {e}")
                return {}

        return {}

    def save_message(self, room: str, message: Dict) -> bool:
        """Save a message to a JSON file."""
        try:
            if room not in self.messages:
                self.messages[room] = []

            message_data = {
                "name": message["name"],
                "message": message["message"],
                "timestamp": datetime.now().isoformat(),
                "id": len(self.messages[room]),
            }
            self.messages[room].append(message_data)
            with open(self.message_file, "w") as f:
                json.dump(self.messages, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return False

    def load_room_messages(self, room: str) -> list:
        """Load all messages for a given room."""
        return self.messages.get(room, [])
