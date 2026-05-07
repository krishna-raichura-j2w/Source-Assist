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

                CREATE TABLE IF NOT EXISTS otps (
                    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email      VARCHAR(255) NOT NULL,
                    otp_code   VARCHAR(6)   NOT NULL,
                    expires_at TIMESTAMPTZ  NOT NULL,
                    is_used    BOOLEAN      DEFAULT FALSE,
                    created_at TIMESTAMPTZ  DEFAULT NOW()
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

                CREATE TABLE IF NOT EXISTS api_cost_log (
                    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
                    email           VARCHAR(255)   NOT NULL,
                    model           VARCHAR(100)   NOT NULL,
                    endpoint        VARCHAR(100)   NOT NULL,
                    input_tokens    INTEGER        NOT NULL DEFAULT 0,
                    output_tokens   INTEGER        NOT NULL DEFAULT 0,
                    total_tokens    INTEGER        NOT NULL DEFAULT 0,
                    input_cost_usd  NUMERIC(12, 8) NOT NULL DEFAULT 0,
                    output_cost_usd NUMERIC(12, 8) NOT NULL DEFAULT 0,
                    total_cost_usd  NUMERIC(12, 8) NOT NULL DEFAULT 0,
                    created_at      TIMESTAMPTZ    DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_otps_email          ON otps(email);
                CREATE INDEX IF NOT EXISTS idx_activity_user_id    ON activity_log(user_id);
                CREATE INDEX IF NOT EXISTS idx_activity_created_at ON activity_log(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_cost_user_id        ON api_cost_log(user_id);
                CREATE INDEX IF NOT EXISTS idx_cost_created_at     ON api_cost_log(created_at DESC);
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


# ── OTPs ──────────────────────────────────────────────────────────────────

def save_otp(email: str, otp_code: str):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE otps SET is_used = TRUE WHERE email = %s AND is_used = FALSE", (email,))
            cur.execute(
                "INSERT INTO otps (email, otp_code, expires_at) VALUES (%s, %s, NOW() + INTERVAL '10 minutes')",
                (email, otp_code),
            )


def check_and_use_otp(email: str, otp_code: str) -> bool:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM otps
                WHERE email = %s AND otp_code = %s AND is_used = FALSE AND expires_at > NOW()
                ORDER BY created_at DESC LIMIT 1
                """,
                (email, otp_code),
            )
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE otps SET is_used = TRUE WHERE id = %s", (row["id"],))
                return True
            return False


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


# ── API cost log ───────────────────────────────────────────────────────────

def log_api_cost(
    user_id: str,
    email: str,
    model: str,
    endpoint: str,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    input_cost_usd: float,
    output_cost_usd: float,
    total_cost_usd: float,
):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO api_cost_log
                    (user_id, email, model, endpoint,
                     input_tokens, output_tokens, total_tokens,
                     input_cost_usd, output_cost_usd, total_cost_usd)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, email, model, endpoint,
                 input_tokens, output_tokens, total_tokens,
                 input_cost_usd, output_cost_usd, total_cost_usd),
            )


def get_cost_stats(user_id: str | None = None) -> dict:
    """Return aggregated cost stats. Pass user_id to scope to one user, None for all."""
    with get_db() as conn:
        with conn.cursor() as cur:
            where = "WHERE user_id = %s" if user_id else ""
            params = (user_id,) if user_id else ()
            cur.execute(
                f"""
                SELECT
                    COUNT(*)                        AS total_calls,
                    COALESCE(SUM(input_tokens),  0) AS total_input_tokens,
                    COALESCE(SUM(output_tokens), 0) AS total_output_tokens,
                    COALESCE(SUM(total_tokens),  0) AS total_tokens,
                    COALESCE(SUM(input_cost_usd),  0) AS total_input_cost_usd,
                    COALESCE(SUM(output_cost_usd), 0) AS total_output_cost_usd,
                    COALESCE(SUM(total_cost_usd),  0) AS total_cost_usd
                FROM api_cost_log {where}
                """,
                params,
            )
            summary = _row(cur.fetchone())
            cur.execute(
                f"""
                SELECT model, endpoint, input_tokens, output_tokens, total_tokens,
                       input_cost_usd, output_cost_usd, total_cost_usd, created_at
                FROM api_cost_log {where}
                ORDER BY created_at DESC LIMIT 50
                """,
                params,
            )
            recent = [_row(r) for r in cur.fetchall()]
    return {
        "total_calls":          int(summary["total_calls"]          or 0),
        "total_input_tokens":   int(summary["total_input_tokens"]   or 0),
        "total_output_tokens":  int(summary["total_output_tokens"]  or 0),
        "total_tokens":         int(summary["total_tokens"]         or 0),
        "total_input_cost_usd": float(summary["total_input_cost_usd"]  or 0),
        "total_output_cost_usd":float(summary["total_output_cost_usd"] or 0),
        "total_cost_usd":       float(summary["total_cost_usd"]        or 0),
        "recent":               recent,
    }
