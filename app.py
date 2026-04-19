from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, date
import calendar

from init_db import init_database
init_database()

from db import (
    get_progress_stats,
    get_category_detail,
    # constants
    CATEGORIES, LABELS, PRIORITIES, get_all_categories,
    # projects
    get_all_projects, get_project_by_id, create_project, update_project, delete_project,
    # sprints
    get_sprints_by_project, get_sprint_by_id, get_active_sprint,
    create_sprint, start_sprint, complete_sprint,
    # tasks
    get_backlog, get_sprint_tasks, get_task_by_id, get_subtasks,
    get_task_comments, create_task, update_task, move_task_status,
    assign_tasks_to_sprint, remove_task_from_sprint, delete_task,
    add_comment, delete_comment, duplicate_task,
    # events
    get_events_by_project, get_upcoming_events, create_event, delete_event,
    # calendar
    get_tasks_for_month, get_tasks_for_date,
    # stats & dashboard
    get_dashboard_stats, get_todo_panel_tasks,
    # log
    get_activity_log,
)

app = Flask(__name__)
app.secret_key = 'deskflo-secret-2026'


@app.template_filter('short_date')
def short_date_filter(value):
    if not value:
        return ''
    try:
        d = datetime.strptime(str(value), '%Y-%m-%d')
        return d.strftime('%a, %d %b')
    except Exception:
        return str(value)


# ─────────────────────────────────────────────────────────────────────────────
# CONTEXT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def current_month_calendar():
    """Return year, month, and a calendar matrix for the current month."""
    today = date.today()
    cal   = calendar.monthcalendar(today.year, today.month)
    return today.year, today.month, cal, today.day


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD  /
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    stats             = get_dashboard_stats()
    todo_tasks        = get_todo_panel_tasks()
    upcoming_tasks    = sorted(todo_tasks, key=lambda t: (t['due_date'] or '9999-99-99'))
    projects          = get_all_projects()
    progress_data     = get_progress_stats()
    category_progress = progress_data['by_category']

    # Collect tasks from ALL active sprints — build per-sprint snapshots for left panel
    active_sprint    = None
    sprint_tasks     = []
    sprint_snapshots = []
    active_project_ids = []
    pri = {'critical': 1, 'high': 2, 'medium': 3, 'low': 4}
    for p in projects:
        s = get_active_sprint(p['project_id'])
        if s:
            if active_sprint is None:
                active_sprint = s  # keep first for the banner display
            tasks = get_sprint_tasks(s['sprint_id'])
            sprint_tasks.extend(tasks)
            active_project_ids.append(p['project_id'])
            total    = len(tasks)
            done     = sum(1 for t in tasks if t['status'] == 'done')
            top_task = next((t for t in sorted(tasks, key=lambda t: pri.get(t['priority'], 5))
                             if t['status'] == 'todo'), None)
            sprint_snapshots.append({
                'sprint':       s,
                'project_name': p['name'],
                'total':        total,
                'done':         done,
                'pct':          int(done / total * 100) if total else 0,
                'top_task':     top_task,
            })

    # Board columns — all sorted by priority
    by_priority = lambda t: pri.get(t['priority'], 5)
    board = {
        'todo':       sorted([t for t in sprint_tasks if t['status'] == 'todo'],       key=by_priority),
        'inprogress': sorted([t for t in sprint_tasks if t['status'] == 'inprogress'], key=by_priority),
        'done':       sorted([t for t in sprint_tasks if t['status'] == 'done'],       key=by_priority),
    }

    # Upcoming events from active-sprint projects
    upcoming_events = get_upcoming_events(active_project_ids) if active_project_ids else []

    # Calendar
    year, month, cal_matrix, today_day = current_month_calendar()
    month_tasks   = get_tasks_for_month(year, month)
    due_dates     = {t['due_date'] for t in month_tasks}
    month_name    = calendar.month_name[month]

    return render_template('index.html',
        stats             = stats,
        todo_tasks        = todo_tasks,
        upcoming_tasks    = upcoming_tasks,
        sprint_snapshots  = sprint_snapshots,
        projects          = projects,
        active_sprint     = active_sprint,
        board             = board,
        upcoming_events   = upcoming_events,
        cal_matrix        = cal_matrix,
        year              = year,
        month             = month,
        month_name        = month_name,
        today_day         = today_day,
        due_dates         = due_dates,
        today_str         = date.today().isoformat(),
        category_progress = category_progress,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PROJECTS
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/projects')
def projects_page():
    projects = get_all_projects()
    return render_template('projects.html', projects=projects, categories=get_all_categories())


@app.route('/projects/create', methods=['POST'])
def create_project_route():
    name        = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    category    = request.form.get('category', 'Personal')

    if not name:
        flash('Project name is required.', 'error')
        return redirect(url_for('projects_page'))

    create_project(name, description, category)
    flash(f'Project "{name}" created!', 'success')
    return redirect(url_for('projects_page'))


@app.route('/projects/<int:project_id>')
def project_detail(project_id):
    project  = get_project_by_id(project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('projects_page'))

    sprints       = get_sprints_by_project(project_id)
    active_sprint = get_active_sprint(project_id)
    backlog_tasks = get_backlog(project_id)
    backlog_count = len(backlog_tasks)
    events        = get_events_by_project(project_id)

    return render_template('project_detail.html',
        project       = project,
        sprints       = sprints,
        active_sprint = active_sprint,
        backlog_tasks = backlog_tasks,
        backlog_count = backlog_count,
        events        = events,
        categories    = get_all_categories(),
        priorities    = PRIORITIES,
        labels        = LABELS,
        today_str     = date.today().isoformat(),
    )


@app.route('/projects/<int:project_id>/edit', methods=['POST'])
def edit_project_route(project_id):
    name        = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    category    = request.form.get('category', 'Personal')

    if not name:
        flash('Project name is required.', 'error')
        return redirect(url_for('project_detail', project_id=project_id))

    update_project(project_id, name, description, category)
    flash('Project updated.', 'success')
    return redirect(url_for('project_detail', project_id=project_id))


@app.route('/projects/<int:project_id>/delete', methods=['POST'])
def delete_project_route(project_id):
    confirm = request.form.get('confirm_delete', '').strip()
    if confirm != 'DELETE':
        flash('Confirmation failed. Type DELETE in all caps to confirm.', 'error')
        return redirect(url_for('project_detail', project_id=project_id))
    delete_project(project_id)
    flash('Project permanently deleted.', 'success')
    return redirect(url_for('projects_page'))


# ─────────────────────────────────────────────────────────────────────────────
# SPRINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/projects/<int:project_id>/sprints/create', methods=['POST'])
def create_sprint_route(project_id):
    name       = request.form.get('name', '').strip()
    goal       = request.form.get('goal', '').strip()
    start_date = request.form.get('start_date', '').strip()
    end_date   = request.form.get('end_date', '').strip()

    errors = []
    if not name:       errors.append('Sprint name is required.')
    if not start_date: errors.append('Start date is required.')
    if not end_date:   errors.append('End date is required.')
    if start_date and end_date and start_date > end_date:
        errors.append('Start date must be before end date.')

    if errors:
        for e in errors:
            flash(e, 'error')
        return redirect(url_for('project_detail', project_id=project_id))

    create_sprint(project_id, name, goal, start_date, end_date)
    flash(f'Sprint "{name}" created!', 'success')
    return redirect(url_for('project_detail', project_id=project_id))


@app.route('/sprints/<int:sprint_id>/start', methods=['POST'])
def start_sprint_route(sprint_id):
    sprint = get_sprint_by_id(sprint_id)
    ok, msg = start_sprint(sprint_id)
    if ok:
        flash(msg, 'success')
    else:
        flash(msg, 'error')
    return redirect(url_for('project_detail', project_id=sprint['project_id']))


@app.route('/sprints/<int:sprint_id>/complete', methods=['POST'])
def complete_sprint_route(sprint_id):
    sprint = get_sprint_by_id(sprint_id)
    ok, msg, summary = complete_sprint(sprint_id)
    if ok:
        flash(
            f'Sprint complete! ✅ {summary["done"]}/{summary["total"]} tasks done. '
            f'{summary["pushed_back"]} task(s) returned to backlog.',
            'success'
        )
    else:
        flash(msg, 'error')
    return redirect(url_for('project_detail', project_id=sprint['project_id']))


@app.route('/sprints/<int:sprint_id>/board')
def sprint_board(sprint_id):
    sprint  = get_sprint_by_id(sprint_id)
    if not sprint:
        flash('Sprint not found.', 'error')
        return redirect(url_for('index'))

    project = get_project_by_id(sprint['project_id'])
    tasks   = get_sprint_tasks(sprint_id)

    board = {
        'todo':       [t for t in tasks if t['status'] == 'todo'],
        'inprogress': [t for t in tasks if t['status'] == 'inprogress'],
        'done':       [t for t in tasks if t['status'] == 'done'],
    }

    # Calendar for toggle view
    year, month, cal_matrix, today_day = current_month_calendar()
    month_tasks = get_tasks_for_month(year, month)
    due_dates   = {t['due_date'] for t in month_tasks}
    month_name  = calendar.month_name[month]

    return render_template('sprint_board.html',
        sprint     = sprint,
        project    = project,
        board      = board,
        all_tasks  = tasks,
        cal_matrix = cal_matrix,
        year       = year,
        month      = month,
        month_name = month_name,
        today_day  = today_day,
        due_dates  = due_dates,
        categories = CATEGORIES,
        labels     = LABELS,
        priorities = PRIORITIES,
        today_str  = date.today().isoformat(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# TASKS
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/projects/<int:project_id>/backlog/create', methods=['POST'])
def create_task_route(project_id):
    title       = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    priority    = request.form.get('priority', 'medium')
    label       = request.form.get('label', '').strip()
    category    = request.form.get('category', 'Personal')
    due_date    = request.form.get('due_date', '').strip() or None
    sprint_id   = request.form.get('sprint_id', '').strip() or None

    if not title:
        flash('Task title is required.', 'error')
        return redirect(request.referrer or url_for('project_detail', project_id=project_id))
    if not due_date:
        flash('Due date is required.', 'error')
        return redirect(request.referrer or url_for('project_detail', project_id=project_id))

    task_id = create_task(project_id, title, description, priority, label, category, due_date, sprint_id=sprint_id)
    subtask_titles = request.form.getlist('subtask_titles')
    for st in subtask_titles:
        st = st.strip()
        if st:
            create_task(project_id, st, '', 'medium', label, category, None,
                        sprint_id=sprint_id, parent_task_id=task_id)

    flash(f'Task "{title}" added!', 'success')
    return redirect(request.referrer or url_for('project_detail', project_id=project_id))


@app.route('/tasks/<int:task_id>/edit', methods=['POST'])
def edit_task_route(task_id):
    title       = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    priority    = request.form.get('priority', 'medium')
    label       = request.form.get('label', '').strip()
    category    = request.form.get('category', 'Personal')
    due_date    = request.form.get('due_date', '').strip() or None

    if not title:
        flash('Task title is required.', 'error')
        return redirect(request.referrer or url_for('index'))

    update_task(task_id, title, description, priority, label, category, due_date)
    flash(f'Task updated.', 'success')
    return redirect(request.referrer or url_for('index'))


@app.route('/tasks/<int:task_id>/subtask/create', methods=['POST'])
def create_subtask_route(task_id):
    parent      = get_task_by_id(task_id)
    title       = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    priority    = request.form.get('priority', 'medium')
    due_date    = request.form.get('due_date', '').strip() or None

    if not title:
        flash('Subtask title is required.', 'error')
        return redirect(request.referrer or url_for('index'))

    create_task(
        parent['project_id'], title, description, priority,
        parent['label'], parent['category'], due_date,
        sprint_id=parent['sprint_id'], parent_task_id=task_id
    )
    flash(f'Subtask "{title}" added!', 'success')
    return redirect(request.referrer or url_for('index'))


@app.route('/backlog/assign-bulk', methods=['POST'])
def assign_bulk_route():
    task_ids   = request.form.getlist('task_ids')
    sprint_id  = request.form.get('sprint_id')
    project_id = request.form.get('project_id')

    if not task_ids:
        flash('No tasks selected.', 'error')
        return redirect(url_for('project_detail', project_id=project_id))
    if not sprint_id:
        flash('Please select a sprint.', 'error')
        return redirect(url_for('project_detail', project_id=project_id))

    assign_tasks_to_sprint([int(t) for t in task_ids], int(sprint_id))
    flash(f'{len(task_ids)} task(s) added to sprint!', 'success')
    return redirect(url_for('project_detail', project_id=project_id))


@app.route('/tasks/<int:task_id>/remove-from-sprint', methods=['POST'])
def remove_from_sprint_route(task_id):
    task = get_task_by_id(task_id)
    remove_task_from_sprint(task_id)
    flash('Task returned to backlog.', 'success')
    return redirect(request.referrer or url_for('project_detail', project_id=task['project_id']))


@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
def delete_task_route(task_id):
    task       = get_task_by_id(task_id)
    project_id = task['project_id'] if task else None
    delete_task(task_id)
    flash('Task deleted.', 'success')
    if project_id:
        return redirect(request.referrer or url_for('project_detail', project_id=project_id))
    return redirect(url_for('index'))


@app.route('/tasks/<int:task_id>/comment', methods=['POST'])
def add_comment_route(task_id):
    content = request.form.get('content', '').strip()
    if content:
        add_comment(task_id, content)
        flash('Comment added.', 'success')
    return redirect(request.referrer or url_for('index'))


@app.route('/comments/<int:comment_id>/delete', methods=['POST'])
def delete_comment_route(comment_id):
    delete_comment(comment_id)
    flash('Comment deleted.', 'success')
    return redirect(request.referrer or url_for('index'))


@app.route('/backlog/duplicate-bulk', methods=['POST'])
def duplicate_bulk_route():
    task_ids   = request.form.getlist('task_ids')
    project_id = request.form.get('project_id')
    if not task_ids:
        flash('No tasks selected.', 'error')
        return redirect(url_for('project_detail', project_id=project_id))
    for tid in task_ids:
        duplicate_task(int(tid))
    flash(f'{len(task_ids)} task(s) duplicated to backlog!', 'success')
    return redirect(url_for('project_detail', project_id=project_id))


# ─────────────────────────────────────────────────────────────────────────────
# EVENTS
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/projects/<int:project_id>/events/create', methods=['POST'])
def create_event_route(project_id):
    title       = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    on_date     = request.form.get('on_date', '').strip()
    on_time     = request.form.get('on_time', '').strip() or None
    location    = request.form.get('location', '').strip() or None

    if not title:
        flash('Event title is required.', 'error')
        return redirect(url_for('project_detail', project_id=project_id))
    if not on_date:
        flash('Event date is required.', 'error')
        return redirect(url_for('project_detail', project_id=project_id))

    create_event(project_id, title, description, on_date, on_time, location)
    flash(f'Event "{title}" created!', 'success')
    return redirect(url_for('project_detail', project_id=project_id))


@app.route('/events/<int:event_id>/delete', methods=['POST'])
def delete_event_route(event_id):
    delete_event(event_id)
    flash('Event deleted.', 'success')
    return redirect(request.referrer or url_for('index'))


# ─────────────────────────────────────────────────────────────────────────────
# ACTIVITY LOG
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/log')
def activity_log_page():
    project_id = request.args.get('project_id', type=int)
    logs       = get_activity_log(project_id=project_id)
    projects   = get_all_projects()
    return render_template('activity_log.html',
        logs       = logs,
        projects   = projects,
        filter_pid = project_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# API ENDPOINTS  (used by frontend JS — drag & drop, calendar, task detail)
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/tasks/<int:task_id>/move', methods=['POST'])
def api_move_task(task_id):
    data       = request.get_json()
    new_status = data.get('status')
    ok, msg    = move_task_status(task_id, new_status)
    if ok:
        return jsonify({'success': True, 'message': msg})
    return jsonify({'success': False, 'error': msg}), 400


@app.route('/api/tasks/<int:task_id>')
def api_get_task(task_id):
    task = get_task_by_id(task_id)
    if not task:
        return jsonify({'error': 'Not found'}), 404
    subtasks = get_subtasks(task_id)
    comments = get_task_comments(task_id)
    return jsonify({
        'task_id':        task['task_id'],
        'title':          task['title'],
        'description':    task['description'] or '',
        'status':         task['status'],
        'priority':       task['priority'],
        'label':          task['label'] or '',
        'category':       task['category'] or '',
        'due_date':       task['due_date'] or '',
        'created_at':     task['created_at'],
        'updated_at':     task['updated_at'],
        'subtask_count':  len(subtasks),
        'subtasks': [
            {
                'task_id':  s['task_id'],
                'title':    s['title'],
                'status':   s['status'],
                'priority': s['priority'],
                'due_date': s['due_date'] or '',
            } for s in subtasks
        ],
        'comments': [
            {
                'comment_id': c['comment_id'],
                'content':    c['content'],
                'created_at': c['created_at'],
            } for c in comments
        ],
    })


@app.route('/api/calendar/<int:year>/<int:month>')
def api_calendar(year, month):
    tasks   = get_tasks_for_month(year, month)
    by_date = {}
    for t in tasks:
        d = t['due_date']
        if d not in by_date:
            by_date[d] = []
        by_date[d].append({
            'task_id':  t['task_id'],
            'title':    t['title'],
            'status':   t['status'],
            'priority': t['priority'],
            'project':  t['project_name'],
        })
    return jsonify(by_date)


@app.route('/api/calendar/date/<string:date_str>')
def api_calendar_date(date_str):
    tasks = get_tasks_for_date(date_str)
    return jsonify([{
        'task_id':  t['task_id'],
        'title':    t['title'],
        'status':   t['status'],
        'priority': t['priority'],
        'project':  t['project_name'],
        'due_date': t['due_date'],
    } for t in tasks])


@app.route('/api/tasks/<int:task_id>/subtask/complete', methods=['POST'])
def api_complete_subtask(task_id):
    ok, msg = move_task_status(task_id, 'done')
    if ok:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': msg}), 400


# ─────────────────────────────────────────────────────────────────────────────
# PROGRESS PAGE
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/progress/<path:category>')
def progress_category(category):
    data = get_category_detail(category)
    return render_template('progress_category.html', category=category, data=data)


@app.route('/progress')
def progress_page():
    data     = get_progress_stats()
    projects = get_all_projects()
    return render_template('progress.html', data=data, projects=projects)


# ─────────────────────────────────────────────────────────────────────────────
# ERROR HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ─────────────────────────────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5003)
