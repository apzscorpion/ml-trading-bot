"""
WebSocket connection manager for broadcasting messages.
Includes latency tagging, sequence numbers, and exponential backoff.
"""
from fastapi import WebSocket
from typing import Dict, Set, Optional
from datetime import datetime
import logging
import asyncio
import time
import itertools

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and subscriptions"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: Dict[WebSocket, Dict] = {}
        self.message_queues: Dict[WebSocket, asyncio.Queue] = {}
        self._send_tasks: Dict[WebSocket, asyncio.Task] = {}
        
        # Sequence numbers for out-of-order message handling
        self.sequence_counter = itertools.count(start=1)
        
        # Connection metadata for latency tracking
        self.connection_metadata: Dict[WebSocket, Dict] = {}
        
        # Reconnection tracking for exponential backoff
        self.reconnect_attempts: Dict[WebSocket, int] = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        self.message_queues[websocket] = asyncio.Queue(maxsize=100)
        
        # Initialize connection metadata
        self.connection_metadata[websocket] = {
            "connected_at": time.time(),
            "last_message_time": time.time(),
            "messages_sent": 0
        }
        
        # Reset reconnect attempts on successful connection
        if websocket in self.reconnect_attempts:
            self.reconnect_attempts[websocket] = 0
        
        # Start background sender task
        self._send_tasks[websocket] = asyncio.create_task(
            self._message_sender(websocket)
        )
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def _get_sequence_number(self) -> int:
        """Get next sequence number for message ordering"""
        return next(self.sequence_counter)
    
    def _calculate_backoff_delay(self, websocket: WebSocket) -> float:
        """
        Calculate exponential backoff delay for reconnection.
        
        Args:
            websocket: WebSocket connection
        
        Returns:
            Delay in seconds
        """
        attempts = self.reconnect_attempts.get(websocket, 0)
        # Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 60s
        delay = min(2 ** attempts, 60)
        return delay
    
    async def _message_sender(self, websocket: WebSocket):
        """Background task to send messages from queue with latency tracking"""
        queue = self.message_queues.get(websocket)
        if not queue:
            return
        
        try:
            while websocket in self.active_connections:
                try:
                    # Wait for message with timeout to allow periodic checks
                    message = await asyncio.wait_for(queue.get(), timeout=1.0)
                    
                    # Track latency: time from message creation to send
                    send_start_time = time.time()
                    message_timestamp = message.get("_timestamp", send_start_time)
                    latency_ms = (send_start_time - message_timestamp) * 1000
                    
                    # Update message with latency if not already set
                    if "_latency_ms" not in message:
                        message["_latency_ms"] = round(latency_ms, 2)
                    
                    await websocket.send_json(message)
                    queue.task_done()
                    
                    # Update connection metadata
                    if websocket in self.connection_metadata:
                        meta = self.connection_metadata[websocket]
                        meta["last_message_time"] = send_start_time
                        meta["messages_sent"] = meta.get("messages_sent", 0) + 1
                    
                except asyncio.TimeoutError:
                    # No message in queue, continue waiting
                    continue
                except Exception as e:
                    logger.error(f"Error sending message to {websocket}: {e}")
                    break
        except Exception as e:
            logger.error(f"Message sender error for {websocket}: {e}")
        finally:
            # Cleanup
            if websocket in self.message_queues:
                del self.message_queues[websocket]
            if websocket in self._send_tasks:
                task = self._send_tasks.pop(websocket)
                if not task.done():
                    task.cancel()
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        if websocket in self.message_queues:
            del self.message_queues[websocket]
        # Use pop with default to avoid KeyError
        if websocket in self._send_tasks:
            task = self._send_tasks.pop(websocket)
            if not task.done():
                task.cancel()
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]
        if websocket in self.reconnect_attempts:
            # Increment reconnect attempts for potential reconnection
            self.reconnect_attempts[websocket] = self.reconnect_attempts.get(websocket, 0) + 1
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    def subscribe(self, websocket: WebSocket, symbol: str, timeframe: str):
        """Subscribe a connection to symbol updates"""
        self.subscriptions[websocket] = {
            "symbol": symbol,
            "timeframe": timeframe
        }
        logger.info(f"WebSocket subscribed to {symbol} {timeframe}")
    
    def get_all_subscriptions(self):
        """Get all active subscriptions"""
        subscriptions = []
        for connection in self.active_connections:
            if connection in self.subscriptions:
                subscriptions.append(self.subscriptions[connection])
        return subscriptions
    
    async def broadcast_candle(self, symbol: str, timeframe: str, candle: Dict):
        """Broadcast candle update with queuing, latency tracking, and sequence numbers"""
        base_message = {
            "type": "candle:update",
            "symbol": symbol,
            "timeframe": timeframe,
            "candle": candle,
            "_timestamp": time.time(),  # Track when message was created
            "_sequence": self._get_sequence_number()  # Sequence number for ordering
        }
        
        disconnected = set()
        for connection in self.active_connections:
            sub = self.subscriptions.get(connection, {})
            if sub.get("symbol") == symbol and sub.get("timeframe") == timeframe:
                queue = self.message_queues.get(connection)
                if queue:
                    try:
                        # Create connection-specific message copy with connection metadata
                        message = base_message.copy()
                        if connection in self.connection_metadata:
                            meta = self.connection_metadata[connection]
                            message["_connection_age_ms"] = round(
                                (time.time() - meta["connected_at"]) * 1000, 2
                            )
                        
                        queue.put_nowait(message)
                    except asyncio.QueueFull:
                        logger.warning(f"Message queue full for {connection}, dropping message")
                        disconnected.add(connection)
                else:
                    disconnected.add(connection)
        
        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_prediction(self, prediction: Dict):
        """Broadcast prediction update with queuing, latency tracking, and sequence numbers"""
        base_message = {
            "type": "prediction:update",
            **prediction,
            "_timestamp": time.time(),  # Track when message was created
            "_sequence": self._get_sequence_number()  # Sequence number for ordering
        }
        
        symbol = prediction.get("symbol")
        timeframe = prediction.get("timeframe")
        
        disconnected = set()
        for connection in self.active_connections:
            sub = self.subscriptions.get(connection, {})
            if sub.get("symbol") == symbol and sub.get("timeframe") == timeframe:
                queue = self.message_queues.get(connection)
                if queue:
                    try:
                        # Create connection-specific message copy with connection metadata
                        message = base_message.copy()
                        if connection in self.connection_metadata:
                            meta = self.connection_metadata[connection]
                            message["_connection_age_ms"] = round(
                                (time.time() - meta["connected_at"]) * 1000, 2
                            )
                        
                        queue.put_nowait(message)
                    except asyncio.QueueFull:
                        logger.warning(f"Message queue full for {connection}, dropping message")
                        disconnected.add(connection)
                else:
                    disconnected.add(connection)
        
        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_training_progress(self, progress_data: Dict):
        """Broadcast training progress with latency tracking and sequence numbers"""
        base_message = {
            "type": "training:progress",
            "timestamp": datetime.utcnow().isoformat(),
            **progress_data,
            "_timestamp": time.time(),  # Track when message was created
            "_sequence": self._get_sequence_number()  # Sequence number for ordering
        }
        
        disconnected = set()
        for connection in self.active_connections:
            queue = self.message_queues.get(connection)
            if queue:
                try:
                    # Create connection-specific message copy
                    message = base_message.copy()
                    if connection in self.connection_metadata:
                        meta = self.connection_metadata[connection]
                        message["_connection_age_ms"] = round(
                            (time.time() - meta["connected_at"]) * 1000, 2
                        )
                    
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    logger.warning(f"Message queue full for {connection}, dropping training progress")
                    disconnected.add(connection)
            else:
                disconnected.add(connection)
        
        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)
    
    def get_reconnect_delay(self, websocket: WebSocket) -> float:
        """
        Get recommended reconnect delay using exponential backoff.
        Call this from client-side before attempting reconnection.
        
        Args:
            websocket: WebSocket connection
        
        Returns:
            Recommended delay in seconds
        """
        return self._calculate_backoff_delay(websocket)


# Singleton instance
manager = ConnectionManager()

