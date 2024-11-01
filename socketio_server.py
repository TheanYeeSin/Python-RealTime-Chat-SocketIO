from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room, send
from message_server import MessageServer
import logging
from datetime import datetime
import os
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_flask_app():
    """Create the Flask application"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "RANDOM_SECRET_KEY"
    return app


def create_socketio_app(app: Flask):
    """Create the SocketIO application"""
    socketio = SocketIO(app)
    message_server = MessageServer()

    @socketio.on("message")
    def handle_message(data):
        try:
            room = data.get("room")
            if not room:
                logger.error("No room specified in message")
                emit("error", {"message": "Room not specified"})
                return
            if not data.get("name") or not data.get("message"):
                logger.error("Invalid message format")
                emit("error", {"message": "Invalid message format"})
                return
            logger.info(f"Message received in room {room}: {data}")
            if message_server.save_message(room, data):
                send(data, to=room)
            else:
                emit("error", {"message": "Failed to save message"})
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            emit("error", {"message": "Internal server error"})

    @socketio.on("join")
    def handle_join(data):
        try:
            room = data.get("room")
            name = data.get("name")

            if not room or not name:
                emit("error", {"message": "Room and name are required"})
                return

            join_room(room)

            previous_messages = message_server.load_room_messages(room)

            if previous_messages:
                emit("chat_history", previous_messages)

            join_message = {
                "name": "System",
                "message": f"{name} joined the room",
                "timestamp": datetime.now().isoformat(),
            }

            send(join_message, to=room)
            logger.info(f"User {name} joined room {room}")

        except Exception as e:
            logger.error(f"Error handling join: {str(e)}")
            emit("error", {"message": "Failed to join room"})

    @socketio.on("leave")
    def handle_leave(data):
        try:
            room = data.get("room")
            name = data.get("name")

            if not room or not name:
                emit("error", {"message": "Room and name are required"})
                return

            leave_room(room)
            leave_message = {
                "name": "System",
                "message": f"{name} left the room",
                "timestamp": datetime.now().isoformat(),
            }
            send(leave_message, to=room)
            logger.info(f"User {name} left room {room}")

        except Exception as e:
            logger.error(f"Error handling leave: {str(e)}")
            emit("error", {"message": "Failed to leave room"})

    @socketio.on_error()
    def error_handler(e):
        logger.error(f"SocketIO error: {str(e)}")
        emit("error", {"message": "An error occurred"})

    return socketio


if __name__ == "__main__":

    app = create_flask_app()
    socketio = create_socketio_app(app)

    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("DEBUG", "False").lower() == "true"

    logger.info(f"Starting server on {host}:{port} (debug={debug})")
    socketio.run(app, host=host, port=port, debug=debug)
