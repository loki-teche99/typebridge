from app.storage.database import Database
import time

class TypingQueue:
    def __init__(self):
        self.db = Database()
        self._resume_typing_to_pending()
        
    def _resume_typing_to_pending(self):
        self.db.execute_queue("UPDATE typing_queue SET status = 'PENDING' WHERE status = 'TYPING'")
        
    def enqueue(self, msg_id, text):
        self.db.execute_queue(
            "INSERT INTO typing_queue (msg_id, text, status, received_at) VALUES (?, ?, ?, ?)",
            (msg_id, text, 'PENDING', int(time.time()))
        )
        
    def get_pending(self):
        rows = self.db.execute_queue("SELECT msg_id, text FROM typing_queue WHERE status = 'PENDING' ORDER BY id ASC")
        return [{'msg_id': r[0], 'text': r[1]} for r in rows]
        
    def mark_typing(self, msg_id):
        self.db.execute_queue("UPDATE typing_queue SET status = 'TYPING' WHERE msg_id = ?", (msg_id,))
        
    def mark_done(self, msg_id):
        self.db.execute_queue("UPDATE typing_queue SET status = 'DONE', completed_at = ? WHERE msg_id = ?", (int(time.time()), msg_id))
        
    def mark_failed(self, msg_id):
        self.db.execute_queue("UPDATE typing_queue SET status = 'FAILED', completed_at = ? WHERE msg_id = ?", (int(time.time()), msg_id))
        
    def clear_pending(self):
        self.db.execute_queue("UPDATE typing_queue SET status = 'CANCELLED' WHERE status IN ('PENDING', 'TYPING')")

    def get_stats(self):
        today = int(time.time()) - (int(time.time()) % 86400)
        rows = self.db.execute_queue("SELECT count(*) FROM typing_queue WHERE status = 'DONE' AND completed_at >= ?", (today,))
        return rows[0][0] if rows else 0
