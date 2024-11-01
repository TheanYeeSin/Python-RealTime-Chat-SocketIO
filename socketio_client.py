import argparse
import socketio
from typing import Optional
from datetime import datetime
import time
import threading
import sys
import os

import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="chat.log",
)
logger = logging.getLogger(__name__)


class MessageClient:
    def __init__(self, server_url: str = "http://localhost:8080"):
        self.sio = socketio.Client(logger=False, engineio_logger=False)
        self.server_url = server_url
        self.connected = False
        self.name: Optional[str] = None
        self.room: Optional[str] = None
        self.input_lock = threading.Lock()
        self.setup_socket_handlers()

    def clear_current_line(self):
        """Clear the current line in terminal"""
        sys.stdout.write("\r" + " " * 100 + "\r")
        sys.stdout.flush()

    def print_message(self, message: str):
        """Print message with proper formatting"""
        with self.input_lock:
            self.clear_current_line()
            print(message)
            if self.name:
                sys.stdout.write(f"{self.name}: ")
                sys.stdout.flush()

    def setup_socket_handlers(self):
        """Setup socket handlers."""

        @self.sio.on("connect")
        def on_connect():
            """Connect to the server"""
            self.connected = True
            logger.info("Connected to server")
            if self.room and self.name:
                self.join_room(self.room, self.name)

        @self.sio.on("disconnect")
        def on_disconnect():
            """Disconnect from the server"""
            self.connected = False
            self.print_message("\nDisconnected from server")

        @self.sio.on("message")
        def on_message(data):
            """Handle receiving messages from server"""
            timestamp = data.get("timestamp", datetime.now().strftime("%H:%M:%S"))
            name = data.get("name", "Unknown")
            message = data.get("message", "")

            if name == "System":
                self.print_message(f"[{timestamp}] {message}")
            else:
                self.print_message(f"[{timestamp}] {name}: {message}")

        @self.sio.on("chat_history")
        def on_chat_history(messages):
            """Handle receiving chat history when joining a room"""
            for message in messages:
                timestamp = message.get(
                    "timestamp", datetime.now().strftime("%H:%M:%S")
                )
                name = message.get("name", "Unknown")
                message = message.get("message", "")
                if name == "System":
                    self.print_message(f"[{timestamp}] {message}")
                else:
                    self.print_message(f"[{timestamp}] {name}: {message}")

        @self.sio.on("error")
        def on_error(data):
            error_msg = data.get("message", "Unknown error occurred")
            logger.error(f"Server error: {error_msg}")

    def connect_to_server(self) -> bool:
        """Connect to the server."""
        retry_count = 0
        max_retries = 3

        while not self.connected and retry_count < max_retries:
            try:
                logger.info(f"Connecting to server at {self.server_url}...")
                self.sio.connect(self.server_url)
                return True
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    logger.error(f"Error connecting to server: {e}. Retrying...")
                    time.sleep(1)
                else:
                    logger.error(
                        f"Error connecting to server: {e}. Max retries exceeded."
                    )
                    return False

        return False

    def join_room(self, room: str, name: str) -> bool:
        """Join a room."""
        try:
            self.room = room
            self.name = name
            logger.info(f"Joining room {room} as {name}...")
            self.sio.emit("join", {"room": room, "name": name})
            return True
        except Exception as e:
            logger.error(f"Error joining room: {e}")
            return False

    def send_message(self, message: str) -> bool:
        """Send a message to the server."""
        if not message.strip():
            return

        try:
            self.sio.emit(
                "message", {"room": self.room, "name": self.name, "message": message}
            )
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    def leave_room(self) -> bool:
        """Leave a room."""
        if self.room and self.name:
            try:
                self.sio.emit("leave", {"room": self.room, "name": self.name})
                return True
            except Exception as e:
                logger.error(f"Error leaving room: {e}")
                return False

    def disconnect(self) -> bool:
        """Disconnect from the server."""
        if self.connected:
            try:
                self.leave_room()
                self.sio.disconnect()
                self.connected = False
                return True
            except Exception as e:
                logger.error(f"Error disconnecting from server: {e}")
                return False


def parse_arguments():
    parser = argparse.ArgumentParser(description="SocketIO Client")

    parser.add_argument("--server_url", default="http://localhost:8080")
    parser.add_argument("--name", help="Your name")
    parser.add_argument("--room", help="Room to join")

    return parser.parse_args()


def main():

    args = parse_arguments()

    client = MessageClient(server_url=args.server_url)

    client.name = args.name or input("Enter your name: ").strip()
    while not client.name:
        client.name = input("Name cannot be empty. Enter your name: ").strip()

    client.room = args.room or input("Enter room number: ").strip()
    while not client.room:
        client.room = input("Room cannot be empty. Enter room number: ").strip()

    if not client.connect_to_server():
        logger.error("Failed to connect to server. Exiting...")
        return

    print("\nWelcome to the chat room!")
    print("Type 'exit' to quit, 'help' for commands")
    print("----------------------------------------")
    try:
        while True:
            message = input(f"{client.name}: ").strip()

            if message.lower() == "exit":
                break
            elif message.lower() == "help":
                client.print_message("\nAvailable commands:")
                client.print_message("  exit - Exit the chat")
                client.print_message("  help - Show this help message")
                continue
            elif message.lower() == "clear":
                os.system("cls" if os.name == "nt" else "clear")
                continue

            if not client.connected:
                client.print_message(
                    "Not connected to server. Attempting to reconnect..."
                )
                if not client.connect_to_server():
                    client.print_message("Reconnection failed. Exiting...")
                    break

            client.send_message(message)

    except KeyboardInterrupt:
        client.print_message("\nExiting chat...")
    except Exception as e:
        client.print_message(f"Unexpected error: {str(e)}")
    finally:
        client.disconnect()
        print("Goodbye!")


if __name__ == "__main__":
    main()
