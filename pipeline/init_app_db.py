import sqlite3
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DB_FILE = ROOT_DIR / "data" / "app_data.db"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    target = db_path or DB_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    return conn


def init_app_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            source_mode TEXT,
            company_name TEXT,
            contact_name TEXT,
            contact_phone TEXT,
            contact_role TEXT,
            industry TEXT,
            business_type_guess TEXT,
            power_load_requirement TEXT,
            estimated_load_kw REAL,
            budget_hint TEXT,
            core_needs_json TEXT,
            concerns_json TEXT,
            current_stage TEXT,
            needs_review INTEGER,
            review_reasons_json TEXT,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS opportunity_followups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id INTEGER,
            user_id TEXT,
            followup_status TEXT,
            followup_note TEXT,
            next_action TEXT,
            next_followup_date TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (opportunity_id) REFERENCES opportunities (id)
        );

        CREATE TABLE IF NOT EXISTS opportunity_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id INTEGER NOT NULL,
            user_id TEXT,
            contact_name TEXT,
            contact_phone TEXT,
            contact_role TEXT,
            contact_source TEXT,
            is_primary INTEGER DEFAULT 1,
            context_note TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (opportunity_id) REFERENCES opportunities (id)
        );

        CREATE INDEX IF NOT EXISTS idx_opportunity_followups_opportunity_id
        ON opportunity_followups (opportunity_id);

        CREATE INDEX IF NOT EXISTS idx_opportunity_contacts_opportunity_id
        ON opportunity_contacts (opportunity_id);
        """
    )
    conn.commit()


def main() -> None:
    with get_connection() as conn:
        init_app_db(conn)
    print(f"Initialized SQLite app database: {DB_FILE}")


if __name__ == "__main__":
    main()
