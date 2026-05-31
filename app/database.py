import os
import aiosqlite
import secrets
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", "data/mindflow.db")

async def init_db():
    Path("data").mkdir(exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                access_until DATETIME,
                plan TEXT DEFAULT 'free',
                invited_by INTEGER,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inviter_id INTEGER NOT NULL,
                invited_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS access_tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at DATETIME NOT NULL,
                used INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def create_user(user_id, username, full_name, invited_by=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (id, username, full_name, access_until, plan, invited_by) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, full_name, datetime.now().isoformat(), 'free', invited_by),
        )
        await db.commit()

async def add_access_days(user_id: int, days: int, plan: str = 'paid'):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT access_until FROM users WHERE id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        if row:
            now = datetime.now()
            current = datetime.fromisoformat(row[0]) if row[0] else now
            base = max(current, now)
            new_until = base + timedelta(days=days)
            await db.execute(
                "UPDATE users SET access_until = ?, plan = ? WHERE id = ?",
                (new_until.isoformat(), plan, user_id)
            )
            await db.commit()

async def has_access(user_id: int) -> bool:
    user = await get_user(user_id)
    if not user or not user.get("access_until"):
        return False
    return datetime.fromisoformat(user["access_until"]) > datetime.now()

async def get_plan(user_id: int) -> str:
    user = await get_user(user_id)
    if not user:
        return 'free'
    if not await has_access(user_id):
        return 'free'
    return user.get("plan", "free")

async def register_referral(inviter_id: int, invited_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM referrals WHERE invited_id = ?", (invited_id,)) as cur:
            if await cur.fetchone():
                return False
        await db.execute(
            "INSERT INTO referrals (inviter_id, invited_id) VALUES (?, ?)",
            (inviter_id, invited_id)
        )
        await db.commit()
    await add_access_days(inviter_id, 7, 'trial')
    await add_access_days(invited_id, 7, 'trial')
    return True

async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE access_until > ?",
            (datetime.now().isoformat(),)
        ) as cur:
            active = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM referrals") as cur:
            refs = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE plan = 'paid' AND access_until > ?",
            (datetime.now().isoformat(),)
        ) as cur:
            paid = (await cur.fetchone())[0]
    return {"total": total, "active": active, "referrals": refs, "paid": paid}

async def get_all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM users") as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]

async def get_days_left(user_id: int) -> int:
    user = await get_user(user_id)
    if not user or not user.get("access_until"):
        return 0
    delta = datetime.fromisoformat(user["access_until"]) - datetime.now()
    return max(0, delta.days)

async def create_access_token(user_id: int, hours: int = 24) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now() + timedelta(hours=hours)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO access_tokens (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires.isoformat())
        )
        await db.commit()
    return token

async def validate_token(token: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM access_tokens WHERE token = ? AND used = 0 AND expires_at > ?",
            (token, datetime.now().isoformat())
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return None
        await db.execute("UPDATE access_tokens SET used = 1 WHERE token = ?", (token,))
        await db.commit()
        return dict(row)
