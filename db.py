import sqlite3
import os
from datetime import datetime, date, timedelta

DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deskflo.db')

# ── Categories & Labels ───────────────────────────────────────────────────────
CATEGORIES = ['Health', 'Finances', 'Academics', 'Career', 'Personal', 'Development', 'Home']

def get_all_categories():
    """Return default categories merged with any custom ones already used in the DB."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM tasks WHERE category IS NOT NULL AND category != '' ORDER BY category")
    db_cats = [r['category'] for r in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT category FROM projects WHERE category IS NOT NULL AND category != '' ORDER BY category")
    db_cats += [r['category'] for r in cursor.fetchall()]
    conn.close()
    merged = list(dict.fromkeys(CATEGORIES + [c for c in db_cats if c not in CATEGORIES]))
    return merged
LABELS     = ['Feature', 'Bug', 'Improvement', 'Research', 'Other']
PRIORITIES = ['low', 'medium', 'high', 'critical']
STATUSES   = ['todo', 'inprogress', 'done']

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode=WAL')
    return conn

def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def log_activity(cursor, action, details, project_id=None, task_id=None):
    cursor.execute('''
        INSERT INTO activity_log (project_id, task_id, action, details, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (project_id, task_id, action, details, now()))


# ─────────────────────────────────────────────────────────────────────────────
# PROJECTS
# ─────────────────────────────────────────────────────────────────────────────

def get_all_projects():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*,
               COUNT(DISTINCT t.task_id)  as task_count,
               COUNT(DISTINCT s.sprint_id) as sprint_count,
               CASE WHEN EXISTS (
                   SELECT 1 FROM sprints s2
                   WHERE s2.project_id = p.project_id AND s2.status = 'active'
               ) THEN 1 ELSE 0 END as has_active_sprint,
               (SELECT COUNT(*) FROM sprints s3
                JOIN tasks t2 ON t2.sprint_id = s3.sprint_id
                WHERE s3.project_id = p.project_id
                  AND s3.status = 'active'
                  AND t2.status != 'done') as active_open_tasks
        FROM projects p
        LEFT JOIN tasks t ON t.project_id = p.project_id
        LEFT JOIN sprints s ON s.project_id = p.project_id
        GROUP BY p.project_id
        ORDER BY p.created_at DESC
    ''')
    projects = cursor.fetchall()
    conn.close()
    return projects

def get_project_by_id(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM projects WHERE project_id = ?', (project_id,))
    project = cursor.fetchone()
    conn.close()
    return project

def create_project(name, description, category):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = now()
    cursor.execute('''
        INSERT INTO projects (name, description, category, status, created_at)
        VALUES (?, ?, ?, 'active', ?)
    ''', (name, description, category, timestamp))
    conn.commit()
    project_id = cursor.lastrowid
    log_activity(cursor, 'project_created', f'Project "{name}" created', project_id=project_id)
    conn.commit()
    conn.close()
    return project_id

def update_project(project_id, name, description, category):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE projects SET name = ?, description = ?, category = ?
        WHERE project_id = ?
    ''', (name, description, category, project_id))
    log_activity(cursor, 'project_updated', f'Project "{name}" updated', project_id=project_id)
    conn.commit()
    conn.close()

def archive_project(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE projects SET status = "archived" WHERE project_id = ?', (project_id,))
    log_activity(cursor, 'project_archived', 'Project archived', project_id=project_id)
    conn.commit()
    conn.close()

def delete_project(project_id):
    """Permanently delete a project and ALL associated data (tasks, sprints, logs)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Delete in dependency order to satisfy FK constraints:
    # comments and activity_log entries ref tasks → delete before tasks
    # subtasks ref parent tasks (self-FK) → delete subtasks before parents
    cursor.execute('DELETE FROM task_comments WHERE task_id IN (SELECT task_id FROM tasks WHERE project_id = ?)', (project_id,))
    cursor.execute('DELETE FROM activity_log WHERE task_id IN (SELECT task_id FROM tasks WHERE project_id = ?)', (project_id,))
    cursor.execute('DELETE FROM tasks WHERE project_id = ? AND parent_task_id IS NOT NULL', (project_id,))
    cursor.execute('DELETE FROM tasks WHERE project_id = ?', (project_id,))
    cursor.execute('DELETE FROM sprints WHERE project_id = ?', (project_id,))
    cursor.execute('DELETE FROM activity_log WHERE project_id = ?', (project_id,))
    cursor.execute('DELETE FROM projects WHERE project_id = ?', (project_id,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# SPRINTS
# ─────────────────────────────────────────────────────────────────────────────

def get_sprints_by_project(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*,
               COUNT(t.task_id) as task_count,
               SUM(CASE WHEN t.status = 'done' THEN 1 ELSE 0 END) as done_count
        FROM sprints s
        LEFT JOIN tasks t ON t.sprint_id = s.sprint_id
        WHERE s.project_id = ?
        GROUP BY s.sprint_id
        ORDER BY s.created_at DESC
    ''', (project_id,))
    sprints = cursor.fetchall()
    conn.close()
    return sprints

def get_sprint_by_id(sprint_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sprints WHERE sprint_id = ?', (sprint_id,))
    sprint = cursor.fetchone()
    conn.close()
    return sprint

def get_active_sprint(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM sprints
        WHERE project_id = ? AND status = 'active'
        LIMIT 1
    ''', (project_id,))
    sprint = cursor.fetchone()
    conn.close()
    return sprint

def create_sprint(project_id, name, goal, start_date, end_date):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = now()
    cursor.execute('''
        INSERT INTO sprints (project_id, name, goal, start_date, end_date, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'planning', ?)
    ''', (project_id, name, goal, start_date, end_date, timestamp))
    conn.commit()
    sprint_id = cursor.lastrowid
    log_activity(cursor, 'sprint_created', f'Sprint "{name}" created', project_id=project_id)
    conn.commit()
    conn.close()
    return sprint_id

def start_sprint(sprint_id):
    """Set sprint to active. Only one sprint can be active per project."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT project_id, name FROM sprints WHERE sprint_id = ?', (sprint_id,))
    sprint = cursor.fetchone()
    if not sprint:
        conn.close()
        return False, 'Sprint not found'
    project_id = sprint['project_id']
    # Check no other sprint is already active
    cursor.execute('''
        SELECT sprint_id FROM sprints
        WHERE project_id = ? AND status = 'active'
    ''', (project_id,))
    active = cursor.fetchone()
    if active:
        conn.close()
        return False, 'Another sprint is already active for this project'
    # Block starting an empty sprint
    cursor.execute('SELECT COUNT(*) as c FROM tasks WHERE sprint_id = ? AND parent_task_id IS NULL', (sprint_id,))
    task_count = cursor.fetchone()['c']
    if task_count == 0:
        conn.close()
        return False, 'Sprint has no tasks. Add tasks from the backlog before starting.'
    cursor.execute('UPDATE sprints SET status = "active" WHERE sprint_id = ?', (sprint_id,))
    log_activity(cursor, 'sprint_started', f'Sprint "{sprint["name"]}" started', project_id=project_id)
    conn.commit()
    conn.close()
    return True, 'Sprint started'

def complete_sprint(sprint_id):
    """
    Complete a sprint. Any tasks not done are automatically
    pushed back to the backlog (sprint_id = NULL).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sprints WHERE sprint_id = ?', (sprint_id,))
    sprint = cursor.fetchone()
    if not sprint:
        conn.close()
        return False, 'Sprint not found', {}
    project_id = sprint['project_id']
    # Count tasks
    cursor.execute('SELECT COUNT(*) as c FROM tasks WHERE sprint_id = ?', (sprint_id,))
    total = cursor.fetchone()['c']
    cursor.execute('SELECT COUNT(*) as c FROM tasks WHERE sprint_id = ? AND status = "done"', (sprint_id,))
    done = cursor.fetchone()['c']
    pushed_back = total - done
    # Push incomplete tasks back to backlog
    cursor.execute('''
        UPDATE tasks SET sprint_id = NULL, updated_at = ?
        WHERE sprint_id = ? AND status != 'done'
    ''', (now(), sprint_id))
    # Mark sprint complete
    timestamp = now()
    cursor.execute('''
        UPDATE sprints SET status = "completed", completed_at = ?
        WHERE sprint_id = ?
    ''', (timestamp, sprint_id))
    log_activity(cursor, 'sprint_completed',
                 f'Sprint "{sprint["name"]}" completed — {done}/{total} tasks done, {pushed_back} returned to backlog',
                 project_id=project_id)
    conn.commit()
    conn.close()
    summary = {'total': total, 'done': done, 'pushed_back': pushed_back}
    return True, 'Sprint completed', summary

def update_sprint(sprint_id, name, goal, start_date, end_date):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT project_id FROM sprints WHERE sprint_id = ?', (sprint_id,))
    sprint = cursor.fetchone()
    cursor.execute('''
        UPDATE sprints SET name = ?, goal = ?, start_date = ?, end_date = ?
        WHERE sprint_id = ?
    ''', (name, goal, start_date, end_date, sprint_id))
    log_activity(cursor, 'sprint_updated', f'Sprint "{name}" updated', project_id=sprint['project_id'])
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# TASKS
# ─────────────────────────────────────────────────────────────────────────────

def get_backlog(project_id):
    """All main tasks (no parent) not assigned to any sprint."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*,
               COUNT(s.task_id) as subtask_count,
               SUM(CASE WHEN s.status = 'done' THEN 1 ELSE 0 END) as subtask_done
        FROM tasks t
        LEFT JOIN tasks s ON s.parent_task_id = t.task_id
        WHERE t.project_id = ? AND t.sprint_id IS NULL AND t.parent_task_id IS NULL
        GROUP BY t.task_id
        ORDER BY
            CASE t.priority
                WHEN 'critical' THEN 1
                WHEN 'high'     THEN 2
                WHEN 'medium'   THEN 3
                WHEN 'low'      THEN 4
            END,
            t.created_at DESC
    ''', (project_id,))
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def get_sprint_tasks(sprint_id):
    """All main tasks in a sprint, grouped by status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*,
               COUNT(s.task_id) as subtask_count,
               SUM(CASE WHEN s.status = 'done' THEN 1 ELSE 0 END) as subtask_done
        FROM tasks t
        LEFT JOIN tasks s ON s.parent_task_id = t.task_id
        WHERE t.sprint_id = ? AND t.parent_task_id IS NULL
        GROUP BY t.task_id
        ORDER BY
            CASE t.priority
                WHEN 'critical' THEN 1
                WHEN 'high'     THEN 2
                WHEN 'medium'   THEN 3
                WHEN 'low'      THEN 4
            END
    ''', (sprint_id,))
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def get_task_by_id(task_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
    task = cursor.fetchone()
    conn.close()
    return task

def get_subtasks(parent_task_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM tasks
        WHERE parent_task_id = ?
        ORDER BY created_at ASC
    ''', (parent_task_id,))
    subtasks = cursor.fetchall()
    conn.close()
    return subtasks

def get_task_comments(task_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM task_comments
        WHERE task_id = ?
        ORDER BY created_at ASC
    ''', (task_id,))
    comments = cursor.fetchall()
    conn.close()
    return comments

def create_task(project_id, title, description, priority, label, category,
                due_date, sprint_id=None, parent_task_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = now()
    cursor.execute('''
        INSERT INTO tasks
        (project_id, sprint_id, parent_task_id, title, description,
         status, priority, label, category, due_date, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'todo', ?, ?, ?, ?, ?, ?)
    ''', (project_id, sprint_id, parent_task_id, title, description,
          priority, label, category, due_date, timestamp, timestamp))
    conn.commit()
    task_id = cursor.lastrowid
    action = 'subtask_created' if parent_task_id else 'task_created'
    log_activity(cursor, action, f'Task "{title}" created', project_id=project_id, task_id=task_id)
    conn.commit()
    conn.close()
    return task_id

def update_task(task_id, title, description, priority, label, category, due_date):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT project_id FROM tasks WHERE task_id = ?', (task_id,))
    task = cursor.fetchone()
    cursor.execute('''
        UPDATE tasks
        SET title = ?, description = ?, priority = ?, label = ?,
            category = ?, due_date = ?, updated_at = ?
        WHERE task_id = ?
    ''', (title, description, priority, label, category, due_date, now(), task_id))
    log_activity(cursor, 'task_updated', f'Task "{title}" updated',
                 project_id=task['project_id'], task_id=task_id)
    conn.commit()
    conn.close()

def move_task_status(task_id, new_status):
    """
    Move a task to a new status.
    ENFORCED: A main task cannot be set to 'done' if it has incomplete subtasks.
    """
    if new_status not in STATUSES:
        return False, f'Invalid status: {new_status}'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
    task = cursor.fetchone()
    if not task:
        conn.close()
        return False, 'Task not found'
    # Subtask enforcement — only block main tasks moving to done
    if new_status == 'done' and task['parent_task_id'] is None:
        cursor.execute('''
            SELECT COUNT(*) as c FROM tasks
            WHERE parent_task_id = ? AND status != 'done'
        ''', (task_id,))
        incomplete = cursor.fetchone()['c']
        if incomplete > 0:
            conn.close()
            return False, f'Cannot complete task — {incomplete} subtask(s) still incomplete'
    cursor.execute('''
        UPDATE tasks SET status = ?, updated_at = ? WHERE task_id = ?
    ''', (new_status, now(), task_id))
    log_activity(cursor, 'task_moved',
                 f'Task "{task["title"]}" moved to {new_status}',
                 project_id=task['project_id'], task_id=task_id)
    conn.commit()
    conn.close()
    return True, 'Status updated'

def assign_tasks_to_sprint(task_ids, sprint_id):
    """Move a list of backlog tasks into a sprint."""
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = now()
    cursor.execute('SELECT project_id, name FROM sprints WHERE sprint_id = ?', (sprint_id,))
    sprint = cursor.fetchone()
    for task_id in task_ids:
        cursor.execute('''
            UPDATE tasks SET sprint_id = ?, updated_at = ? WHERE task_id = ?
        ''', (sprint_id, timestamp, task_id))
        log_activity(cursor, 'task_added_to_sprint',
                     f'Task added to sprint "{sprint["name"]}"',
                     project_id=sprint['project_id'], task_id=task_id)
    conn.commit()
    conn.close()

def remove_task_from_sprint(task_id):
    """Send a task back to the backlog."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT project_id, title FROM tasks WHERE task_id = ?', (task_id,))
    task = cursor.fetchone()
    cursor.execute('UPDATE tasks SET sprint_id = NULL, updated_at = ? WHERE task_id = ?', (now(), task_id))
    log_activity(cursor, 'task_removed_from_sprint',
                 f'Task "{task["title"]}" returned to backlog',
                 project_id=task['project_id'], task_id=task_id)
    conn.commit()
    conn.close()

def delete_task(task_id):
    """Delete a task and all its subtasks and comments."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT project_id, title FROM tasks WHERE task_id = ?', (task_id,))
    task = cursor.fetchone()
    if not task:
        conn.close()
        return False
    # Delete subtasks first
    cursor.execute('DELETE FROM tasks WHERE parent_task_id = ?', (task_id,))
    # Delete comments
    cursor.execute('DELETE FROM task_comments WHERE task_id = ?', (task_id,))
    # Delete task
    cursor.execute('DELETE FROM tasks WHERE task_id = ?', (task_id,))
    log_activity(cursor, 'task_deleted',
                 f'Task "{task["title"]}" deleted',
                 project_id=task['project_id'])
    conn.commit()
    conn.close()
    return True

def add_comment(task_id, content):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = now()
    cursor.execute('''
        INSERT INTO task_comments (task_id, content, created_at)
        VALUES (?, ?, ?)
    ''', (task_id, content, timestamp))
    cursor.execute('SELECT project_id FROM tasks WHERE task_id = ?', (task_id,))
    task = cursor.fetchone()
    log_activity(cursor, 'comment_added', 'Comment added to task',
                 project_id=task['project_id'], task_id=task_id)
    conn.commit()
    conn.close()

def delete_comment(comment_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM task_comments WHERE comment_id = ?', (comment_id,))
    conn.commit()
    conn.close()

def duplicate_task(task_id):
    """Clone a task into the backlog (no sprint, status=todo, no due_date)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
    task = cursor.fetchone()
    if not task:
        conn.close()
        return None
    timestamp = now()
    cursor.execute('''
        INSERT INTO tasks
        (project_id, sprint_id, parent_task_id, title, description,
         status, priority, label, category, due_date, created_at, updated_at)
        VALUES (?, NULL, NULL, ?, ?, 'todo', ?, ?, ?, NULL, ?, ?)
    ''', (task['project_id'], task['title'] + ' (copy)', task['description'],
          task['priority'], task['label'], task['category'], timestamp, timestamp))
    conn.commit()
    new_id = cursor.lastrowid
    log_activity(cursor, 'task_created', f'Task "{task["title"]}" duplicated',
                 project_id=task['project_id'], task_id=new_id)
    conn.commit()
    conn.close()
    return new_id


# ─────────────────────────────────────────────────────────────────────────────
# EVENTS
# ─────────────────────────────────────────────────────────────────────────────

def get_events_by_project(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM events WHERE project_id = ?
        ORDER BY on_date ASC, on_time ASC
    ''', (project_id,))
    events = cursor.fetchall()
    conn.close()
    return events

def get_upcoming_events(project_ids=None):
    """Get events with on_date >= today, optionally filtered to specific projects."""
    conn = get_db_connection()
    cursor = conn.cursor()
    today = date.today().isoformat()
    if project_ids:
        placeholders = ','.join('?' * len(project_ids))
        cursor.execute(f'''
            SELECT e.*, p.name as project_name
            FROM events e JOIN projects p ON e.project_id = p.project_id
            WHERE e.on_date >= ? AND e.project_id IN ({placeholders})
            ORDER BY e.on_date ASC, e.on_time ASC
        ''', [today] + list(project_ids))
    else:
        cursor.execute('''
            SELECT e.*, p.name as project_name
            FROM events e JOIN projects p ON e.project_id = p.project_id
            WHERE e.on_date >= ?
            ORDER BY e.on_date ASC, e.on_time ASC
        ''', (today,))
    events = cursor.fetchall()
    conn.close()
    return events

def create_event(project_id, title, description, on_date, on_time, location):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = now()
    cursor.execute('''
        INSERT INTO events (project_id, title, description, on_date, on_time, location, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (project_id, title, description, on_date, on_time or None, location or None, timestamp, timestamp))
    conn.commit()
    event_id = cursor.lastrowid
    log_activity(cursor, 'event_created', f'Event "{title}" created', project_id=project_id)
    conn.commit()
    conn.close()
    return event_id

def delete_event(event_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT project_id, title FROM events WHERE event_id = ?', (event_id,))
    event = cursor.fetchone()
    if not event:
        conn.close()
        return False
    cursor.execute('DELETE FROM events WHERE event_id = ?', (event_id,))
    log_activity(cursor, 'event_deleted', f'Event "{event["title"]}" deleted',
                 project_id=event['project_id'])
    conn.commit()
    conn.close()
    return True


# ─────────────────────────────────────────────────────────────────────────────
# CALENDAR
# ─────────────────────────────────────────────────────────────────────────────

def get_tasks_for_month(year, month):
    """Return all tasks with due dates in a given month, across all projects."""
    month_str = f'{year}-{month:02d}'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*, p.name as project_name
        FROM tasks t
        JOIN projects p ON t.project_id = p.project_id
        WHERE t.due_date LIKE ? AND t.parent_task_id IS NULL
        ORDER BY t.due_date ASC
    ''', (f'{month_str}%',))
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def get_tasks_for_date(date_str):
    """Return all tasks due on a specific date."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*, p.name as project_name
        FROM tasks t
        JOIN projects p ON t.project_id = p.project_id
        WHERE t.due_date = ? AND t.parent_task_id IS NULL
        ORDER BY t.priority DESC
    ''', (date_str,))
    tasks = cursor.fetchall()
    conn.close()
    return tasks


# ─────────────────────────────────────────────────────────────────────────────
# STATS (for dashboard progress panel)
# ─────────────────────────────────────────────────────────────────────────────

def get_dashboard_stats():
    conn = get_db_connection()
    cursor = conn.cursor()

    # All-time completed tasks
    cursor.execute("SELECT COUNT(*) as c FROM tasks WHERE status = 'done' AND parent_task_id IS NULL")
    all_time = cursor.fetchone()['c']

    # This month
    month_str = datetime.now().strftime('%Y-%m')
    cursor.execute('''
        SELECT COUNT(*) as c FROM tasks
        WHERE status = 'done' AND parent_task_id IS NULL AND updated_at LIKE ?
    ''', (f'{month_str}%',))
    this_month = cursor.fetchone()['c']

    # Active sprint progress (first active sprint found)
    cursor.execute("SELECT * FROM sprints WHERE status = 'active' LIMIT 1")
    active_sprint = cursor.fetchone()
    sprint_progress = None
    if active_sprint:
        cursor.execute('SELECT COUNT(*) as c FROM tasks WHERE sprint_id = ? AND parent_task_id IS NULL',
                       (active_sprint['sprint_id'],))
        total = cursor.fetchone()['c']
        cursor.execute('''SELECT COUNT(*) as c FROM tasks
                          WHERE sprint_id = ? AND status = 'done' AND parent_task_id IS NULL''',
                       (active_sprint['sprint_id'],))
        done = cursor.fetchone()['c']
        sprint_progress = {
            'name': active_sprint['name'],
            'total': total,
            'done': done,
            'percent': round((done / total * 100) if total > 0 else 0)
        }

    # Streak — consecutive calendar days with at least one task completed
    cursor.execute('''
        SELECT DISTINCT DATE(updated_at) as d FROM tasks
        WHERE status = 'done' AND parent_task_id IS NULL
        ORDER BY d DESC
    ''')
    dates = [row['d'] for row in cursor.fetchall()]
    streak = 0
    check = date.today()
    for d in dates:
        if d == str(check):
            streak += 1
            check = date.fromordinal(check.toordinal() - 1)
        else:
            break

    # Overdue tasks
    today = date.today().isoformat()
    cursor.execute('''
        SELECT COUNT(*) as c FROM tasks
        WHERE due_date < ? AND status != 'done' AND parent_task_id IS NULL
    ''', (today,))
    overdue = cursor.fetchone()['c']

    conn.close()
    return {
        'all_time':       all_time,
        'this_month':     this_month,
        'sprint_progress': sprint_progress,
        'streak':         streak,
        'overdue':        overdue,
    }

def get_todo_panel_tasks():
    """All non-done main tasks in any active sprint — for the left panel."""
    conn = get_db_connection()
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute('''
        SELECT t.*, p.name as project_name, s.name as sprint_name
        FROM tasks t
        JOIN projects p ON t.project_id = p.project_id
        JOIN sprints s ON t.sprint_id = s.sprint_id
        WHERE s.status = 'active'
          AND t.status != 'done'
          AND t.parent_task_id IS NULL
        ORDER BY
            CASE WHEN t.due_date < ? THEN 0 ELSE 1 END,
            CASE t.priority
                WHEN 'critical' THEN 1
                WHEN 'high'     THEN 2
                WHEN 'medium'   THEN 3
                WHEN 'low'      THEN 4
            END
    ''', (today,))
    tasks = cursor.fetchall()
    conn.close()
    return tasks


# ─────────────────────────────────────────────────────────────────────────────
# ACTIVITY LOG
# ─────────────────────────────────────────────────────────────────────────────

def get_activity_log(project_id=None, limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    if project_id:
        cursor.execute('''
            SELECT a.*, p.name as project_name
            FROM activity_log a
            LEFT JOIN projects p ON a.project_id = p.project_id
            WHERE a.project_id = ?
            ORDER BY a.timestamp DESC
            LIMIT ?
        ''', (project_id, limit))
    else:
        cursor.execute('''
            SELECT a.*, p.name as project_name
            FROM activity_log a
            LEFT JOIN projects p ON a.project_id = p.project_id
            ORDER BY a.timestamp DESC
            LIMIT ?
        ''', (limit,))
    logs = cursor.fetchall()
    conn.close()
    return logs


# ─────────────────────────────────────────────────────────────────────────────
# PROGRESS STATS
# ─────────────────────────────────────────────────────────────────────────────

def get_progress_stats():
    conn   = get_db_connection()
    cursor = conn.cursor()
    by_category = {}
    cat_counts  = {}

    # Get all categories that actually have tasks (not just hardcoded list)
    cursor.execute("""
        SELECT category, COUNT(*) as total,
               SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done
        FROM tasks WHERE parent_task_id IS NULL AND category IS NOT NULL AND category != ''
        GROUP BY category ORDER BY category
    """)
    for row in cursor.fetchall():
        cat   = row['category']
        total = row['total'] or 0
        done  = row['done']  or 0
        cat_counts[cat] = {'total': total, 'done': done}
        if total > 0:
            by_category[cat] = round(done / total * 100)

    cursor.execute("""
        SELECT s.name, s.completed_at, s.start_date, s.end_date,
               COUNT(t.task_id) as total,
               SUM(CASE WHEN t.status = 'done' THEN 1 ELSE 0 END) as done
        FROM sprints s
        LEFT JOIN tasks t ON t.sprint_id = s.sprint_id AND t.parent_task_id IS NULL
        WHERE s.status = 'completed'
        GROUP BY s.sprint_id ORDER BY s.completed_at DESC LIMIT 10
    """)
    sprint_history = [dict(r) for r in cursor.fetchall()]
    for s in sprint_history:
        s['velocity'] = round(s['done'] / s['total'] * 100) if s['total'] else 0

    trend = []
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        cursor.execute("SELECT COUNT(*) as c FROM tasks WHERE DATE(updated_at) = ? AND status = 'done' AND parent_task_id IS NULL", (d,))
        trend.append({'date': d, 'count': cursor.fetchone()['c']})

    conn.close()
    return {'by_category': by_category, 'cat_counts': cat_counts,
            'sprint_history': sprint_history, 'weekly_trend': trend}


def get_category_detail(category):
    conn   = get_db_connection()
    cursor = conn.cursor()

    # Totals
    cursor.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done
        FROM tasks WHERE category = ? AND parent_task_id IS NULL
    """, (category,))
    row   = cursor.fetchone()
    total = row['total'] or 0
    done  = row['done']  or 0
    pct   = round(done / total * 100) if total else 0

    today_str  = date.today().isoformat()
    week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    month_start = date.today().replace(day=1).isoformat()

    def count_period(start, end=None):
        if end:
            cursor.execute("""SELECT COUNT(*) as c FROM tasks
                WHERE category=? AND status='done' AND parent_task_id IS NULL
                AND DATE(updated_at) BETWEEN ? AND ?""", (category, start, end))
        else:
            cursor.execute("""SELECT COUNT(*) as c FROM tasks
                WHERE category=? AND status='done' AND parent_task_id IS NULL
                AND DATE(updated_at) = ?""", (category, start))
        return cursor.fetchone()['c']

    today_count = count_period(today_str)
    week_count  = count_period(week_start, today_str)
    month_count = count_period(month_start, today_str)

    # Priority breakdown
    cursor.execute("""
        SELECT priority, COUNT(*) as c FROM tasks
        WHERE category=? AND status='done' AND parent_task_id IS NULL
        GROUP BY priority ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END
    """, (category,))
    by_priority = {r['priority']: r['c'] for r in cursor.fetchall()}

    # Weekly trend
    trend = []
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        cursor.execute("""SELECT COUNT(*) as c FROM tasks
            WHERE category=? AND DATE(updated_at)=? AND status='done' AND parent_task_id IS NULL""", (category, d))
        trend.append({'date': d, 'count': cursor.fetchone()['c']})

    # All completed tasks grouped by day
    cursor.execute("""
        SELECT t.task_id, t.title, t.priority, t.label, t.updated_at,
               p.name as project_name, s.name as sprint_name
        FROM tasks t
        LEFT JOIN projects p ON p.project_id = t.project_id
        LEFT JOIN sprints s ON s.sprint_id = t.sprint_id
        WHERE t.category=? AND t.status='done' AND t.parent_task_id IS NULL
        ORDER BY t.updated_at DESC
    """, (category,))
    rows = cursor.fetchall()
    conn.close()

    by_day = {}
    for r in rows:
        r = dict(r)
        try:
            dt = datetime.fromisoformat(r['updated_at'])
            day_key = dt.strftime('%A, %b %d %Y')
            r['time'] = dt.strftime('%H:%M')
        except Exception:
            day_key = r['updated_at'][:10] if r['updated_at'] else 'Unknown'
            r['time'] = ''
        by_day.setdefault(day_key, []).append(r)

    return {
        'total': total, 'done': done, 'pct': pct,
        'today': today_count, 'this_week': week_count,
        'this_month': month_count, 'all_time': done,
        'by_priority': by_priority,
        'weekly_trend': trend,
        'by_day': by_day,
    }