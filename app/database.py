import os
import aiosqlite
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
            "INSERT OR IGNORE INTO users (id, username, full_name, access_until, invited_by) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, full_name, datetime.now().isoformat(), invited_by),
        )
        await db.commit()

async def add_access_days(user_id: int, days: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT access_until FROM users WHERE id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        if row:
            now = datetime.now()
            current = datetime.fromisoformat(row[0]) if row[0] else now
            base = max(current, now)
            new_until = base + timedelta(days=days)
            await db.execute("UPDATE users SET access_until = ? WHERE id = ?", (new_until.isoformat(), user_id))
            await db.commit()

async def has_access(user_id: int) -> bool:
    user = await get_user(user_id)
    if not user or not user.get("access_until"):
        return False
    return datetime.fromisoformat(user["access_until"]) > datetime.now()

async def register_referral(inviter_id: int, invited_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM referrals WHERE invited_id = ?", (invited_id,)) as cur:
            if await cur.fetchone():
                return False
        await db.execute("INSERT INTO referrals (inviter_id, invited_id) VALUES (?, ?)", (inviter_id, invited_id))
        await db.commit()
    await add_access_days(inviter_id, 7)
    await add_access_days(invited_id, 7)
    return True

async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE access_until > ?", (datetime.now().isoformat(),)) as cur:
            active = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM referrals") as cur:
            refs = (await cur.fetchone())[0]
    return {"total": total, "active": active, "referrals": refs}

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
