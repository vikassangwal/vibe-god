"""
SQLite Database Manager for Wife God Agent
Handles: task logging, user sessions, document tracking, receipts, OTP sessions
"""

import asyncio
import aiosqlite
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import aiosqlite

logger = logging.getLogger("WifeGod.Database")


@dataclass
class TaskLog:
    id: str
    type: str
    status: str
    params: str
    result: str
    error: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class DocumentRecord:
    id: str
    file_path: str
    file_hash: str
    doc_type: str
    extracted_text: str
    structured_data: str
    status: str
    created_at: datetime


@dataclass
class UserSession:
    id: str
    service: str
    username: str
    encrypted_data: str
    created_at: datetime
    expires_at: datetime


@dataclass
class ReceiptRecord:
    id: str
    task_id: str
    service: str
    amount: float
    receipt_path: str
    downloaded_at: datetime


@dataclass
class OTPSession:
    id: str
    task_id: str
    otp_type: str
    status: str
    otp_code: Optional[str]
    created_at: datetime
    expires_at: datetime


class DatabaseManager:
    """SQLite database manager for Wife God Agent"""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[aiosqlite.Connection] = None

    async def initialize(self):
        """Initialize database and create tables"""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row

        await self._create_tables()
        await self._create_indexes()
        logger.info(f"Database initialized at {self.db_path}")

    async def _create_tables(self):
        """Create all required tables"""
        async with self._connection.cursor() as cursor:
            # Task logs table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_logs (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    params TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """)

            # Document records
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    doc_type TEXT,
                    extracted_text TEXT,
                    structured_data TEXT,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            """)

            # User sessions
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id TEXT PRIMARY KEY,
                    service TEXT NOT NULL,
                    username TEXT NOT NULL,
                    encrypted_data TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
            """)

            # Receipts
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS receipts (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    service TEXT NOT NULL,
                    amount REAL NOT NULL,
                    receipt_path TEXT NOT NULL,
                    downloaded_at TIMESTAMP NOT NULL
                )
            """)

            # OTP Sessions
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS otp_sessions (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    otp_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    otp_code TEXT,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
            """)

            # Twitter sessions
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS twitter_sessions (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    session_data TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
            """)

            # Document templates for eMitra
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_templates (
                    id TEXT PRIMARY KEY,
                    service TEXT NOT NULL,
                    doc_type TEXT NOT NULL,
                    size_limit_kb INTEGER,
                    format TEXT,
                    dimensions TEXT,
                    created_at TIMESTAMP NOT NULL
                )
            """)

            # Voice interaction logs
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS voice_logs (
                    id TEXT PRIMARY KEY,
                    task_id TEXT,
                    direction TEXT,
                    text TEXT,
                    audio_path TEXT,
                    created_at TIMESTAMP NOT NULL
                )
            """)

            await self._connection.commit()

    async def _create_indexes(self):
        """Create database indexes for performance"""
        async with self._connection.cursor() as cursor:
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_task_logs_type ON task_logs(type)",
                "CREATE INDEX IF NOT EXISTS idx_task_logs_status ON task_logs(status)",
                "CREATE INDEX IF NOT EXISTS idx_task_logs_created ON task_logs(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(doc_type)",
                "CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)",
                "CREATE INDEX IF NOT EXISTS idx_otp_sessions_task ON otp_sessions(task_id)",
                "CREATE INDEX IF NOT EXISTS idx_receipts_task ON receipts(task_id)",
                "CREATE INDEX IF NOT EXISTS idx_voice_logs_task ON voice_logs(task_id)",
            ]
            for index_sql in indexes:
                await cursor.execute(index_sql)
            await self._connection.commit()

    async def log_task(self, task) -> None:
        """Log task to database"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                INSERT OR REPLACE INTO task_logs
                (id, type, status, params, result, error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id,
                task.type.value if hasattr(task.type, 'value') else str(task.type),
                task.status.value if hasattr(task.status, 'value') else str(task.status),
                json.dumps(task.params, default=str),
                json.dumps(task.result, default=str) if task.result else None,
                task.error,
                task.created_at.isoformat(),
                task.updated_at.isoformat()
            ))
            await self._connection.commit()

    async def get_task(self, task_id: str) -> Optional[Dict]:
        """Get task by ID"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("SELECT * FROM task_logs WHERE id = ?", (task_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_recent_tasks(self, limit: int = 50) -> List[Dict]:
        """Get recent tasks"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "SELECT * FROM task_logs ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # Document operations
    async def save_document(self, doc: DocumentRecord) -> None:
        """Save document record"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                INSERT OR REPLACE INTO documents
                (id, file_path, file_hash, doc_type, extracted_text, structured_data, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc.id, doc.file_path, doc.file_hash, doc.doc_type,
                doc.extracted_text, doc.structured_data, doc.status,
                doc.created_at.isoformat()
            ))
            await self._connection.commit()

    async def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get document by ID"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_documents_by_type(self, doc_type: str) -> List[Dict]:
        """Get documents by type"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "SELECT * FROM documents WHERE doc_type = ? ORDER BY created_at DESC",
                (doc_type,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # User session operations
    async def save_session(self, session: UserSession) -> None:
        """Save user session"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                INSERT OR REPLACE INTO user_sessions
                (id, service, username, encrypted_data, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session.id, session.service, session.username,
                session.encrypted_data, session.created_at.isoformat(),
                session.expires_at.isoformat()
            ))
            await self._connection.commit()

    async def get_session(self, service: str, username: str) -> Optional[Dict]:
        """Get user session"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "SELECT * FROM user_sessions WHERE service = ? AND username = ? AND expires_at > ?",
                (service, username, datetime.now().isoformat())
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    # Receipt operations
    async def save_receipt(self, receipt: ReceiptRecord) -> None:
        """Save receipt record"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                INSERT OR REPLACE INTO receipts
                (id, task_id, service, amount, receipt_path, downloaded_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                receipt.id, receipt.task_id, receipt.service,
                receipt.amount, receipt.receipt_path,
                receipt.downloaded_at.isoformat()
            ))
            await self._connection.commit()

    async def get_receipts_by_task(self, task_id: str) -> List[Dict]:
        """Get receipts by task ID"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "SELECT * FROM receipts WHERE task_id = ?",
                (task_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # OTP session operations
    async def create_otp_session(self, otp: OTPSession) -> None:
        """Create OTP session"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO otp_sessions
                (id, task_id, otp_type, status, otp_code, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                otp.id, otp.task_id, otp.otp_type, otp.status,
                otp.otp_code, otp.created_at.isoformat(),
                otp.expires_at.isoformat()
            ))
            await self._connection.commit()

    async def update_otp_session(self, otp_id: str, status: str, otp_code: str = None) -> None:
        """Update OTP session"""
        async with self._connection.cursor() as cursor:
            if otp_code:
                await cursor.execute(
                    "UPDATE otp_sessions SET status = ?, otp_code = ? WHERE id = ?",
                    (status, otp_code, otp_id)
                )
            else:
                await cursor.execute(
                    "UPDATE otp_sessions SET status = ? WHERE id = ?",
                    (status, otp_id)
                )
            await self._connection.commit()

    async def get_otp_session(self, otp_id: str) -> Optional[Dict]:
        """Get OTP session"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("SELECT * FROM otp_sessions WHERE id = ?", (otp_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_pending_otp(self, task_id: str) -> Optional[Dict]:
        """Get pending OTP for task"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "SELECT * FROM otp_sessions WHERE task_id = ? AND status = 'pending'",
                (task_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    # Twitter session operations
    async def save_twitter_session(self, username: str, session_data: Dict) -> None:
        """Save Twitter session"""
        import uuid
        session_id = str(uuid.uuid4())
        expires = datetime.now().replace(year=datetime.now().year + 1)

        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                INSERT OR REPLACE INTO twitter_sessions
                (id, username, session_data, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id, username, json.dumps(session_data),
                datetime.now().isoformat(), expires.isoformat()
            ))
            await self._connection.commit()

    async def get_twitter_session(self, username: str) -> Optional[Dict]:
        """Get Twitter session"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "SELECT * FROM twitter_sessions WHERE username = ? AND expires_at > ?",
                (username, datetime.now().isoformat())
            )
            row = await cursor.fetchone()
            if row:
                data = dict(row)
                data['session_data'] = json.loads(data['session_data'])
                return data
            return None

    # Document templates
    async def get_template(self, service: str, doc_type: str) -> Optional[Dict]:
        """Get document template"""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "SELECT * FROM document_templates WHERE service = ? AND doc_type = ?",
                (service, doc_type)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def save_template(self, template: Dict) -> None:
        """Save document template"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                INSERT OR REPLACE INTO document_templates
                (id, service, doc_type, size_limit_kb, format, dimensions, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                template['id'], template['service'], template['doc_type'],
                template['size_limit_kb'], template['format'],
                template.get('dimensions', ''), datetime.now().isoformat()
            ))
            await self._connection.commit()

    # Voice logs
    async def log_voice(self, task_id: str, direction: str, text: str, audio_path: str = "") -> None:
        """Log voice interaction"""
        import uuid
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO voice_logs (id, task_id, direction, text, audio_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(uuid.uuid4()), task_id, direction, text, audio_path, datetime.now().isoformat()))
            await self._connection.commit()

    # Statistics
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        async with self._connection.cursor() as cursor:
            stats = {}

            await cursor.execute("SELECT COUNT(*) FROM task_logs")
            stats['total_tasks'] = (await cursor.fetchone())[0]

            await cursor.execute("SELECT COUNT(*) FROM documents")
            stats['total_documents'] = (await cursor.fetchone())[0]

            await cursor.execute("SELECT COUNT(*) FROM receipts")
            stats['total_receipts'] = (await cursor.fetchone())[0]

            await cursor.execute("SELECT type, COUNT(*) FROM task_logs GROUP BY type")
            stats['tasks_by_type'] = dict(await cursor.fetchall())

            await cursor.execute("SELECT status, COUNT(*) FROM task_logs GROUP BY status")
            stats['tasks_by_status'] = dict(await cursor.fetchall())

            return stats

    async def close(self):
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            logger.info("Database connection closed")