import sqlite3
import os

DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deskflo.db')

def init_database():
    """Initialize the DeskFlo SQLite database with all required tables."""

    db_exists = os.path.exists(DATABASE_FILE)
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # ── Projects ──────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            project_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            description  TEXT,
            category     TEXT DEFAULT 'Personal',
            status       TEXT DEFAULT 'active',   -- active | archived
            created_at   TEXT NOT NULL
        )
    ''')

    # ── Sprints ───────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sprints (
            sprint_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id   INTEGER NOT NULL,
            name         TEXT NOT NULL,
            goal         TEXT,
            start_date   TEXT,
            end_date     TEXT,
            status       TEXT DEFAULT 'planning', -- planning | active | completed
            created_at   TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (project_id)
        )
    ''')

    # ── Tasks ─────────────────────────────────────────────────────────────────
    # parent_task_id NULL  → main task
    # parent_task_id SET   → subtask of that parent
    # sprint_id NULL       → lives in backlog
    # sprint_id SET        → assigned to that sprint
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id     INTEGER NOT NULL,
            sprint_id      INTEGER,               -- NULL = backlog
            parent_task_id INTEGER,               -- NULL = main task
            title          TEXT NOT NULL,
            description    TEXT,
            status         TEXT DEFAULT 'todo',   -- todo | inprogress | done
            priority       TEXT DEFAULT 'medium', -- low | medium | high | critical
            label          TEXT,                  -- Bug | Feature | Improvement | Research | Other
            category       TEXT DEFAULT 'Personal', -- Health | Finances | Academics | Career | Personal | Development | Home
            due_date       TEXT,
            created_at     TEXT NOT NULL,
            updated_at     TEXT NOT NULL,
            FOREIGN KEY (project_id)     REFERENCES projects (project_id),
            FOREIGN KEY (sprint_id)      REFERENCES sprints  (sprint_id),
            FOREIGN KEY (parent_task_id) REFERENCES tasks    (task_id)
        )
    ''')

    # ── Task Comments ─────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_comments (
            comment_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id     INTEGER NOT NULL,
            content     TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks (task_id)
        )
    ''')

    # ── Activity Log ──────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER,
            task_id     INTEGER,               -- NULL for project/sprint-level actions
            action      TEXT NOT NULL,         -- e.g. task_created, task_moved, sprint_started
            details     TEXT,                  -- human-readable description
            timestamp   TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects (project_id),
            FOREIGN KEY (task_id)    REFERENCES tasks    (task_id)
        )
    ''')

    # ── Events ────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL,
            title       TEXT NOT NULL,
            description TEXT,
            location    TEXT,
            on_date     TEXT NOT NULL,
            on_time     TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects (project_id)
        )
    ''')

    conn.commit()
    conn.close()

    if db_exists:
        print(f"✓ Database '{DATABASE_FILE}' already exists — tables verified.")
    else:
        print(f"✓ Database '{DATABASE_FILE}' created successfully with all tables.")
        print("  Tables: projects, sprints, tasks, task_comments, activity_log")


if __name__ == '__main__':
    init_database()