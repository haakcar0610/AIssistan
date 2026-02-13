import sqlite3
from datetime import datetime
from faissqlite import VectorStore
from sentence_transformers import SentenceTransformer

class Memory:
    def __init__(self, db_path="memory.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.vector_store = VectorStore(db_path=db_path.replace('.db', '_vectors.db'))
        
    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user_memory (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
    
    def save_message(self, user_id, role, content):
        cursor = self.conn.execute(
            "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?) RETURNING id",
            (user_id, role, content)
        )
        msg_id = cursor.fetchone()[0]
        self.conn.commit()
        
        embedding = self.model.encode(content).tolist()
        self.vector_store.add_document(
            text=content,
            embedding=embedding,
            metadata={"user_id": user_id, "role": role, "msg_id": msg_id}
        )
        return msg_id
    
    def get_recent_messages(self, user_id, limit=30):
        cursor = self.conn.execute(
            "SELECT role, content FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )
        return list(reversed(cursor.fetchall()))
    
    def search_similar(self, user_id, query, k=5):
        query_emb = self.model.encode(query).tolist()
        results = self.vector_store.search(query_emb, k=k)
        filtered = [r for r in results if r.get('metadata', {}).get('user_id') == user_id]
        return filtered
    
    def save_user_name(self, user_id, name):
        self.conn.execute(
            "INSERT OR REPLACE INTO user_memory (user_id, name) VALUES (?, ?)",
            (user_id, name)
        )
        self.conn.commit()
    
    def get_user_name(self, user_id):
        cursor = self.conn.execute(
            "SELECT name FROM user_memory WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else None
