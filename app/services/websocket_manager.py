import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger("math_gap.websocket_manager")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accepts a new WebSocket connection and registers it in the connection pool."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("New WebSocket client connected. Active connections: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        """Unregisters a WebSocket client connection from the active pool."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected. Active connections: %d", len(self.active_connections))

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Sends a direct text message to a specific WebSocket client."""
        await websocket.send_text(message)

    async def broadcast(self, message: dict):
        """Broadcasts a JSON-serialized payload to all connected clients concurrently."""
        bad_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as exc:
                logger.warning("Failed to send JSON to WebSocket client. Error: %s", exc)
                bad_connections.append(connection)
                
        # Clean up failed channels
        for bad_conn in bad_connections:
            self.disconnect(bad_conn)
            try:
                await bad_conn.close()
            except Exception:
                pass


# Global singleton connection manager
manager = ConnectionManager()
