"""
TypeBridge Desktop - Message Protocol
Defines message types, builder, and parser for the TypeBridge wire protocol.
"""
import json
import uuid
import time


class MessageType:
    TEXT_PAYLOAD  = "TEXT_PAYLOAD"
    ACK           = "ACK"
    HEARTBEAT     = "HEARTBEAT"
    PAIR_REQUEST  = "PAIR_REQUEST"
    PAIR_RESPONSE = "PAIR_RESPONSE"
    REVOKE        = "REVOKE"
    STATUS        = "STATUS"
    CONTROL       = "CONTROL"


class MessageBuilder:
    @staticmethod
    def build(msg_type: str, payload: str, iv: str, session_id: str) -> str:
        """Serialize a TypeBridge message to a JSON string."""
        msg = {
            "id":         str(uuid.uuid4()),
            "type":       msg_type,
            "payload":    payload,
            "iv":         iv,
            "session_id": session_id,
            "timestamp":  int(time.time() * 1000),
        }
        return json.dumps(msg)


class MessageParser:
    @staticmethod
    def parse(raw: str) -> dict:
        """Parse a JSON string into a message dict. Raises ValueError on bad input."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

        if "type" not in msg:
            raise ValueError("Message missing 'type' field")

        # Ensure required keys exist with defaults
        msg.setdefault("id",         "")
        msg.setdefault("payload",    "")
        msg.setdefault("iv",         "")
        msg.setdefault("session_id", "")
        msg.setdefault("timestamp",  0)
        return msg
