import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

ALLOWED_DOMAINS = {"joulestowatts.com", "joulestowatts.co"}


def _db_kwargs() -> dict:
    """Parse the DB URL manually so passwords containing '@' work correctly."""
    url  = os.getenv("SUPABASE_DB_URL", "")
    rest = url.split("://", 1)[1]
    last_at   = rest.rfind("@")
    userinfo  = rest[:last_at]
    hostinfo  = rest[last_at + 1:]
    user, password = userinfo.split(":", 1)
    host_db   = hostinfo.split("/", 1)
    dbname    = host_db[1] if len(host_db) > 1 else "postgres"
    host_port = host_db[0].rsplit(":", 1)
    host      = host_port[0]
    port      = int(host_port[1]) if len(host_port) > 1 else 5432
    return dict(host=host, port=port, dbname=dbname, user=user, password=password)


@contextmanager
def get_db():
    conn = psycopg2.connect(
        cursor_factory=psycopg2.extras.RealDictCursor,
        **_db_kwargs(),
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _row(r) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


# ── Schema ────────────────────────────────────────────────────────────────

def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email         VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255),
                    is_verified   BOOLEAN DEFAULT FALSE,
                    created_at    TIMESTAMPTZ DEFAULT NOW(),
                    last_login_at TIMESTAMPTZ
                );

                CREATE TABLE IF NOT EXISTS activity_log (
                    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
                    email       VARCHAR(255) NOT NULL,
                    action_type VARCHAR(10)  NOT NULL,
                    image_count INTEGER      DEFAULT 0,
                    status      VARCHAR(10)  DEFAULT 'success',
                    created_at  TIMESTAMPTZ  DEFAULT NOW(),
                    details     JSONB        DEFAULT '{}'::jsonb
                );

                CREATE INDEX IF NOT EXISTS idx_activity_user_id    ON activity_log(user_id);
                CREATE INDEX IF NOT EXISTS idx_activity_created_at ON activity_log(created_at DESC);
            """)


# ── Users ─────────────────────────────────────────────────────────────────

def get_user_by_email(email: str) -> dict | None:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            return _row(cur.fetchone())


def upsert_user(email: str) -> dict:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (email) VALUES (%s)
                ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
                RETURNING *
                """,
                (email,),
            )
            return _row(cur.fetchone())


def set_user_password(email: str, password_hash: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s, is_verified = TRUE WHERE email = %s",
                (password_hash, email),
            )


def update_last_login(user_id: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET last_login_at = NOW() WHERE id = %s", (user_id,))


# ── Activity log ──────────────────────────────────────────────────────────

def log_activity(
    user_id: str,
    email: str,
    action_type: str,
    image_count: int = 0,
    status: str = "success",
    details: dict = None,
):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO activity_log (user_id, email, action_type, image_count, status, details)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, email, action_type, image_count, status,
                 psycopg2.extras.Json(details or {})),
            )


def get_activity_stats(user_id: str) -> dict:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*)                                       AS total,
                    COUNT(*) FILTER (WHERE action_type = 'text')  AS text_count,
                    COUNT(*) FILTER (WHERE action_type = 'image') AS image_count,
                    MAX(created_at)                                AS last_activity
                FROM activity_log
                WHERE user_id = %s AND status = 'success'
                """,
                (user_id,),
            )
            stats  = _row(cur.fetchone())
            cur.execute(
                """
                SELECT action_type, image_count, status, created_at
                FROM activity_log WHERE user_id = %s
                ORDER BY created_at DESC LIMIT 20
                """,
                (user_id,),
            )
            recent = [_row(r) for r in cur.fetchall()]
    return {
        "total_extractions": int(stats["total"]       or 0),
        "text_extractions":  int(stats["text_count"]  or 0),
        "image_extractions": int(stats["image_count"] or 0),
        "last_activity":     stats["last_activity"],
        "recent":            recent,
    }
