import sqlite3
import json
from typing import Dict, Any, List
from threading import Lock
from config import settings
from utils.logger import setup_logger

logger = setup_logger(__name__)


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = Lock()
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        preferences TEXT DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS translations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        source_text TEXT,
                        translated_text TEXT,
                        source_lang TEXT,
                        target_lang TEXT,
                        style TEXT,
                        provider TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                conn.commit()
                logger.info("Database initialized successfully")
            except Exception as e:
                logger.error(f"Database initialization error: {e}")
                raise
            finally:
                conn.close()
    
    def register_user(self, user_id: int, username: str, first_name: str):
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = excluded.username,
                        first_name = excluded.first_name,
                        updated_at = CURRENT_TIMESTAMP
                """, (user_id, username, first_name))
                conn.commit()
            finally:
                conn.close()
    
    def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT preferences FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                if row and row["preferences"]:
                    return json.loads(row["preferences"])
                return {}
            finally:
                conn.close()
    
    def update_user_preferences(self, user_id: int, **kwargs):
        current_prefs = self.get_user_preferences(user_id)
        current_prefs.update(kwargs)
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (user_id, preferences, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id) DO UPDATE SET
                        preferences = excluded.preferences,
                        updated_at = CURRENT_TIMESTAMP
                """, (user_id, json.dumps(current_prefs)))
                conn.commit()
                logger.debug(f"Updated preferences for user {user_id}: {kwargs}")
            finally:
                conn.close()
    
    def save_translation(self, user_id: int, source_text: str, translated_text: str,
                        source_lang: str, target_lang: str, style: str, provider: str):
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO translations 
                    (user_id, source_text, translated_text, source_lang, target_lang, style, provider)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, source_text, translated_text, source_lang, target_lang, style, provider))
                conn.commit()
            finally:
                conn.close()
    
    def get_user_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM translations WHERE user_id = ? 
                    ORDER BY created_at DESC LIMIT ?
                """, (user_id, limit))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()


_db_instance = None

def get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(settings.DATABASE_PATH)
    return _db_instance


def init_db():
    get_db()
