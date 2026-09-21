"""
Fofoqueiro – Persistência SQLite
"""
import sqlite3
import os
from datetime import datetime
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection):
    """Cria as tabelas se ainda não existirem."""
    c = conn.cursor()

    # Migrations seguras para tabelas existentes
    try:
        c.execute("ALTER TABLE news ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    except sqlite3.OperationalError:
        pass  # Coluna já existe

    try:
        c.execute("ALTER TABLE news ADD COLUMN is_starred INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Coluna já existe

    c.executescript("""
        CREATE TABLE IF NOT EXISTS news (
            id           TEXT PRIMARY KEY,
            source       TEXT NOT NULL,
            category     TEXT,
            title        TEXT NOT NULL,
            title_pt     TEXT,
            link         TEXT,
            summary      TEXT,
            cve_id       TEXT,
            severity     TEXT,
            tabcoins     INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,
            published_at TEXT,
            fetched_at   TEXT NOT NULL,
            processed    INTEGER NOT NULL DEFAULT 0,
            status       TEXT NOT NULL DEFAULT 'active',
            is_starred   INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS worker_runs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at    TEXT NOT NULL,
            finished_at   TEXT,
            source        TEXT,
            items_found   INTEGER DEFAULT 0,
            items_new     INTEGER DEFAULT 0,
            status        TEXT DEFAULT 'running'
        );
    """)
    conn.commit()


# ── CRUD News ──────────────────────────────────────────────────────────

def upsert_news(conn: sqlite3.Connection, items: list[dict]):
    """Insere ou atualiza notícias. Retorna quantas eram novas."""
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    new_count = 0
    for item in items:
        c.execute("SELECT id FROM news WHERE id = ?", (item["id"],))
        is_new = c.fetchone() is None
        if is_new:
            new_count += 1
        c.execute("""
            INSERT INTO news
                (id, source, category, title, title_pt, link, summary,
                 cve_id, severity, tabcoins, comment_count, published_at, fetched_at, processed)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0)
            ON CONFLICT(id) DO UPDATE SET
                title        = excluded.title,
                tabcoins     = excluded.tabcoins,
                comment_count= excluded.comment_count,
                fetched_at   = excluded.fetched_at
        """, (
            item["id"],
            item.get("source", ""),
            item.get("category", ""),
            item.get("title", ""),
            item.get("title_pt"),
            item.get("link"),
            item.get("summary"),
            item.get("cve_id"),
            item.get("severity"),
            item.get("tabcoins", 0),
            item.get("comment_count", 0),
            item.get("published_at"),
            now,
        ))
    conn.commit()
    return new_count


def update_summary(conn: sqlite3.Connection, news_id: str, title_pt: str | None, summary: str):
    conn.execute(
        "UPDATE news SET title_pt=?, summary=?, processed=1 WHERE id=?",
        (title_pt, summary, news_id),
    )
    conn.commit()


def update_status(conn: sqlite3.Connection, news_id: str, status: str):
    """Atualiza o estado de uma notícia (ex: 'active', 'archived', 'ignored')."""
    conn.execute(
        "UPDATE news SET status = ? WHERE id = ?",
        (status, news_id),
    )
    conn.commit()


def toggle_starred(conn: sqlite3.Connection, news_id: str):
    """Alterna o status de favorito (is_starred) de uma notícia."""
    conn.execute(
        "UPDATE news SET is_starred = CASE WHEN is_starred = 1 THEN 0 ELSE 1 END WHERE id = ?",
        (news_id,),
    )
    conn.commit()


def get_news(
    conn: sqlite3.Connection,
    source: str | None = None,
    status: str | None = "active",
    only_starred: bool = False,
    limit: int = 100,
    offset: int = 0,
    search: str | None = None,
) -> list[sqlite3.Row]:
    q = "SELECT * FROM news WHERE 1=1"
    params: list = []
    if source:
        q += " AND source = ?"
        params.append(source)
    if status:
        q += " AND status = ?"
        params.append(status)
    if only_starred:
        q += " AND is_starred = 1"
    if search:
        q += " AND (title LIKE ? OR title_pt LIKE ? OR summary LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])
    q += " ORDER BY published_at DESC, fetched_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    return conn.execute(q, params).fetchall()


def get_pending(conn: sqlite3.Connection, limit: int = 30) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM news WHERE processed=0 AND title != '' ORDER BY fetched_at ASC LIMIT ?",
        (limit,),
    ).fetchall()


# ── Worker logs ────────────────────────────────────────────────────────

def start_run(conn: sqlite3.Connection, source: str) -> int:
    c = conn.cursor()
    c.execute(
        "INSERT INTO worker_runs (started_at, source) VALUES (?,?)",
        (datetime.utcnow().isoformat(), source),
    )
    conn.commit()
    return c.lastrowid


def finish_run(conn: sqlite3.Connection, run_id: int, found: int, new: int, status: str = "ok"):
    conn.execute(
        "UPDATE worker_runs SET finished_at=?, items_found=?, items_new=?, status=? WHERE id=?",
        (datetime.utcnow().isoformat(), found, new, status, run_id),
    )
    conn.commit()


def get_recent_runs(conn: sqlite3.Connection, limit: int = 20) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM worker_runs ORDER BY started_at DESC LIMIT ?", (limit,)
    ).fetchall()
