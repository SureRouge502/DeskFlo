"""Populate DeskFlo with realistic demo data."""
import sqlite3, os
from datetime import datetime, date, timedelta

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deskflo.db')

def ts(d: date, h=9, m=0):
    return datetime(d.year, d.month, d.day, h, m).strftime('%Y-%m-%d %H:%M:%S')

def run():
    conn = sqlite3.connect(DB)
    conn.execute('PRAGMA foreign_keys = ON')
    cur = conn.cursor()

    today   = date.today()
    t       = lambda days=0: (today + timedelta(days=days)).isoformat()
    past    = lambda days:    (today - timedelta(days=days)).isoformat()
    past_ts = lambda days, h=10: ts(today - timedelta(days=days), h)
    fut_ts  = lambda days, h=9:  ts(today + timedelta(days=days), h)

    # ── PROJECTS ─────────────────────────────────────────────────────────────
    projects = [
        (1, 'Portfolio Website',    'Personal dev portfolio & blog',           'Development', 'active',   past_ts(40)),
        (2, 'Fitness & Nutrition',  'Track workouts, meals and wellness goals', 'Health',      'active',   past_ts(30)),
        (3, 'Budget Planner 2026',  'Monthly budgeting and savings goals',      'Finances',    'active',   past_ts(20)),
        (4, 'Machine Learning BSc', 'Final-year ML dissertation project',       'Academics',   'active',   past_ts(60)),
        (5, 'Career Growth',        'Job applications, interviews, networking', 'Career',      'active',   past_ts(15)),
    ]
    cur.executemany(
        'INSERT OR REPLACE INTO projects (project_id,name,description,category,status,created_at) VALUES (?,?,?,?,?,?)',
        projects
    )

    # ── SPRINTS ──────────────────────────────────────────────────────────────
    sprints = [
        # id, project_id, name, goal, start, end, status, created_at, completed_at
        (1,  1, 'Sprint 1 – Foundation',  'Set up repo, design system and home page',    past(28), past(15), 'completed', past_ts(30), past_ts(15,18)),
        (2,  1, 'Sprint 2 – Content',     'Projects page, blog and case studies',         past(14), t(0),     'active',    past_ts(15), None),
        (3,  1, 'Sprint 3 – Polish',      'SEO, animations and launch',                   t(1),     t(14),    'planning',  past_ts(2),  None),

        (4,  2, 'Week 1 – Baseline',      'Establish routine and log first week',          past(21), past(14), 'completed', past_ts(22), past_ts(14,20)),
        (5,  2, 'Week 2 – Build Habit',   'Consistent 5-day workout streak',              past(13), past(7),  'completed', past_ts(14), past_ts(7,20)),
        (6,  2, 'Week 3 – Push',          'Increase weights and add meal prep',            past(6),  t(1),     'active',    past_ts(7),  None),

        (7,  3, 'April Budget',           'Track all April expenses vs budget',            past(18), t(12),    'active',    past_ts(20), None),

        (8,  4, 'Literature Review',      'Read and annotate 20 core papers',              past(45), past(20), 'completed', past_ts(47), past_ts(20,17)),
        (9,  4, 'Model Development',      'Build and evaluate baseline CNN model',         past(19), t(3),     'active',    past_ts(21), None),
        (10, 4, 'Write-up Phase 1',       'Draft intro, methodology and related work',    t(4),     t(25),    'planning',  past_ts(1),  None),

        (11, 5, 'Job Search – April',     'Apply to 10 roles, prep for interviews',        past(10), t(20),    'active',    past_ts(12), None),
    ]
    cur.executemany(
        'INSERT OR REPLACE INTO sprints (sprint_id,project_id,name,goal,start_date,end_date,status,created_at,completed_at) VALUES (?,?,?,?,?,?,?,?,?)',
        sprints
    )

    # ── TASKS ─────────────────────────────────────────────────────────────────
    # (id, project_id, sprint_id, parent_task_id, title, description, status, priority, label, category, due_date, created_at, updated_at)
    tasks = [
        # ── Portfolio – Sprint 1 (completed) ──────────────────────────────
        (1,  1, 1, None, 'Initialise Next.js repo',       'Set up with TypeScript and Tailwind',       'done',       'high',     'Feature',     'Development', past(27), past_ts(28), past_ts(18)),
        (2,  1, 1, None, 'Design token system',           'Colours, typography, spacing tokens',       'done',       'high',     'Feature',     'Development', past(22), past_ts(27), past_ts(16)),
        (3,  1, 1, None, 'Build home page hero',          'Animated headline and CTA',                 'done',       'high',     'Feature',     'Development', past(18), past_ts(26), past_ts(15,14)),
        (4,  1, 1, None, 'Configure CI/CD pipeline',      'GitHub Actions → Vercel deploy',            'done',       'medium',   'Feature',     'Development', past(16), past_ts(25), past_ts(15,11)),

        # ── Portfolio – Sprint 2 (active) ─────────────────────────────────
        (5,  1, 2, None, 'Projects showcase page',        'Filter by tech stack, animated cards',      'done',       'high',     'Feature',     'Development', past(7),  past_ts(14), past_ts(5)),
        (6,  1, 2, None, 'Blog MDX integration',          'Parse and render MDX with syntax highlight','inprogress', 'high',     'Feature',     'Development', t(0),     past_ts(12), past_ts(1)),
        (7,  1, 2, None, 'Dark mode toggle',              'System preference + manual override',       'inprogress', 'medium',   'Improvement', 'Development', t(2),     past_ts(10), past_ts(0,15)),
        (8,  1, 2, None, 'Contact form',                  'Formspree integration, validation',         'todo',       'medium',   'Feature',     'Development', t(3),     past_ts(9),  past_ts(9)),
        (9,  1, 2, None, 'Responsive nav',                'Mobile hamburger menu',                     'todo',       'low',      'Improvement', 'Development', t(4),     past_ts(8),  past_ts(8)),

        # subtasks for Blog MDX (task 6)
        (10, 1, 2, 6,    'Install rehype plugins',        '',                                          'done',       'medium',   'Feature',     'Development', t(0),     past_ts(11), past_ts(2)),
        (11, 1, 2, 6,    'Write first blog post',         'Draft "Building this portfolio"',           'inprogress', 'medium',   'Feature',     'Development', t(1),     past_ts(11), past_ts(0,14)),
        (12, 1, 2, 6,    'Add reading time estimate',     '',                                          'todo',       'low',      'Improvement', 'Development', t(2),     past_ts(10), past_ts(10)),

        # ── Portfolio – Backlog (no sprint) ───────────────────────────────
        (13, 1, None, None, 'Add analytics (Plausible)',  'Privacy-first analytics integration',       'todo',       'low',      'Feature',     'Development', t(20),    past_ts(5),  past_ts(5)),
        (14, 1, None, None, 'Write about page',           'Timeline and skills section',               'todo',       'medium',   'Feature',     'Development', t(18),    past_ts(4),  past_ts(4)),

        # ── Fitness – Sprint 4 & 5 (completed) ───────────────────────────
        (15, 2, 4, None, 'Log starting measurements',     'Weight, body fat, resting HR',              'done',       'high',     'Feature',     'Health',      past(21), past_ts(22), past_ts(20)),
        (16, 2, 4, None, 'Complete 3 gym sessions',       'Upper/lower/full-body split',               'done',       'high',     'Feature',     'Health',      past(15), past_ts(21), past_ts(15,19)),
        (17, 2, 5, None, 'Meal prep Sunday',              'Prep 5 lunches for the week',               'done',       'medium',   'Feature',     'Health',      past(13), past_ts(14), past_ts(13,13)),
        (18, 2, 5, None, '5-day workout streak',          'No missed sessions',                        'done',       'high',     'Feature',     'Health',      past(8),  past_ts(13), past_ts(8,18)),

        # ── Fitness – Sprint 6 (active) ───────────────────────────────────
        (19, 2, 6, None, 'Increase bench press 5 kg',     'Progressive overload this week',            'inprogress', 'high',     'Improvement', 'Health',      t(1),     past_ts(6),  past_ts(1)),
        (20, 2, 6, None, 'Track macros daily',            'Hit protein target every day',              'inprogress', 'medium',   'Feature',     'Health',      t(1),     past_ts(6),  past_ts(0,11)),
        (21, 2, 6, None, 'Add 20 min cardio 3×/week',    'Post-weight LISS cardio',                   'todo',       'medium',   'Improvement', 'Health',      t(2),     past_ts(5),  past_ts(5)),
        (22, 2, 6, None, 'Book sports massage',           'Recovery appointment',                      'todo',       'low',      'Other',       'Health',      t(3),     past_ts(5),  past_ts(5)),

        # ── Finances – Sprint 7 (active) ─────────────────────────────────
        (23, 3, 7, None, 'Categorise all March expenses', 'Audit bank statement',                      'done',       'high',     'Research',    'Finances',    past(10), past_ts(18), past_ts(10,16)),
        (24, 3, 7, None, 'Set April budget limits',       'Groceries, entertainment, transport',       'done',       'high',     'Feature',     'Finances',    past(8),  past_ts(17), past_ts(8,12)),
        (25, 3, 7, None, 'Log weekly expenses',           'Every Sunday review',                       'inprogress', 'medium',   'Feature',     'Finances',    t(3),     past_ts(15), past_ts(0,9)),
        (26, 3, 7, None, 'Review subscriptions',          'Cancel unused ones',                        'inprogress', 'medium',   'Research',    'Finances',    t(5),     past_ts(14), past_ts(1,8)),
        (27, 3, 7, None, 'Move £200 to savings',          'Transfer to ISA',                           'todo',       'critical', 'Feature',     'Finances',    t(7),     past_ts(12), past_ts(12)),
        (28, 3, 7, None, 'Research investment options',   'S&P 500 index funds comparison',            'todo',       'low',      'Research',    'Finances',    t(12),    past_ts(10), past_ts(10)),

        # subtasks for subscriptions review (task 26)
        (29, 3, 7, 26,   'List all active subscriptions', '',                                          'done',       'medium',   'Research',    'Finances',    t(2),     past_ts(13), past_ts(1,10)),
        (30, 3, 7, 26,   'Identify duplicates',           '',                                          'inprogress', 'medium',   'Research',    'Finances',    t(4),     past_ts(13), past_ts(0,8)),
        (31, 3, 7, 26,   'Cancel unused services',        '',                                          'todo',       'high',     'Feature',     'Finances',    t(5),     past_ts(12), past_ts(12)),

        # ── Finances – Backlog ────────────────────────────────────────────
        (32, 3, None, None, 'Set up emergency fund',      'Target: 3 months expenses',                 'todo',       'high',     'Feature',     'Finances',    t(30),    past_ts(8),  past_ts(8)),

        # ── ML Dissertation – Sprint 8 (completed) ───────────────────────
        (33, 4, 8, None, 'Collect 20 key papers',         'arXiv and Google Scholar',                  'done',       'critical', 'Research',    'Academics',   past(35), past_ts(44), past_ts(30)),
        (34, 4, 8, None, 'Annotate papers in Zotero',     'Highlight methods and results',             'done',       'high',     'Research',    'Academics',   past(25), past_ts(40), past_ts(22)),
        (35, 4, 8, None, 'Write literature review draft', '3000 words',                                'done',       'critical', 'Research',    'Academics',   past(22), past_ts(35), past_ts(21)),
        (36, 4, 8, None, 'Supervisor feedback session',   'Book meeting, prepare questions',           'done',       'high',     'Other',       'Academics',   past(21), past_ts(30), past_ts(21,15)),

        # ── ML Dissertation – Sprint 9 (active) ──────────────────────────
        (37, 4, 9, None, 'Preprocess dataset',            'Normalise, split train/val/test',           'done',       'critical', 'Feature',     'Academics',   past(10), past_ts(18), past_ts(10,17)),
        (38, 4, 9, None, 'Implement baseline CNN',        'PyTorch, ResNet-18',                        'done',       'critical', 'Feature',     'Academics',   past(5),  past_ts(15), past_ts(5,20)),
        (39, 4, 9, None, 'Train on GPU cluster',          'Submit SLURM job, 50 epochs',               'inprogress', 'critical', 'Feature',     'Academics',   t(2),     past_ts(10), past_ts(0,16)),
        (40, 4, 9, None, 'Evaluate with F1 / AUC',        'Plot ROC curves',                           'todo',       'high',     'Research',    'Academics',   t(3),     past_ts(8),  past_ts(8)),
        (41, 4, 9, None, 'Write experiment notes',        'Keep lab notebook up to date',              'inprogress', 'medium',   'Research',    'Academics',   t(1),     past_ts(7),  past_ts(0,10)),

        # subtasks for CNN training (task 39)
        (42, 4, 9, 39,   'Write SLURM batch script',      '',                                          'done',       'high',     'Feature',     'Academics',   t(0),     past_ts(9),  past_ts(1,8)),
        (43, 4, 9, 39,   'Monitor training loss',         '',                                          'inprogress', 'medium',   'Research',    'Academics',   t(2),     past_ts(8),  past_ts(0,16)),
        (44, 4, 9, 39,   'Save best checkpoint',          '',                                          'todo',       'medium',   'Feature',     'Academics',   t(2),     past_ts(7),  past_ts(7)),

        # ── ML – Backlog ──────────────────────────────────────────────────
        (45, 4, None, None, 'Experiment with transformer','Compare ViT vs CNN on same dataset',        'todo',       'medium',   'Research',    'Academics',   t(35),    past_ts(3),  past_ts(3)),

        # ── Career – Sprint 11 (active) ───────────────────────────────────
        (46, 5, 11, None, 'Update CV and LinkedIn',       'Tailor for ML Engineer roles',              'done',       'critical', 'Feature',     'Career',      past(7),  past_ts(10), past_ts(7,11)),
        (47, 5, 11, None, 'Apply to 10 ML Engineer roles','Focus on fintech and healthtech',           'inprogress', 'critical', 'Feature',     'Career',      t(10),    past_ts(9),  past_ts(0,13)),
        (48, 5, 11, None, 'Prep system design interview', 'Study distributed systems basics',          'inprogress', 'high',     'Research',    'Career',      t(8),     past_ts(8),  past_ts(1,9)),
        (49, 5, 11, None, 'Mock coding interview × 2',    'LeetCode medium, timed sessions',           'todo',       'high',     'Feature',     'Career',      t(5),     past_ts(7),  past_ts(7)),
        (50, 5, 11, None, 'Reach out to 5 connections',   'LinkedIn warm outreach',                    'todo',       'medium',   'Other',       'Career',      t(6),     past_ts(6),  past_ts(6)),
        (51, 5, 11, None, 'Research target companies',    'Culture, tech stack, glassdoor reviews',    'done',       'medium',   'Research',    'Career',      past(5),  past_ts(10), past_ts(5,14)),

        # subtasks for job applications (task 47)
        (52, 5, 11, 47,  'Tailor CV for each role',        '',                                         'inprogress', 'high',     'Feature',     'Career',      t(5),     past_ts(8),  past_ts(0,13)),
        (53, 5, 11, 47,  'Write cover letters × 5',        '',                                         'todo',       'high',     'Feature',     'Career',      t(7),     past_ts(7),  past_ts(7)),
        (54, 5, 11, 47,  'Submit applications',            '',                                         'todo',       'critical', 'Feature',     'Career',      t(10),    past_ts(6),  past_ts(6)),

        # ── Career – Backlog ──────────────────────────────────────────────
        (55, 5, None, None, 'Build ML demo project',       'Deployable Hugging Face Space',             'todo',       'high',     'Feature',     'Career',      t(25),    past_ts(4),  past_ts(4)),
        (56, 5, None, None, 'Write technical blog post',   '"Intro to Transformers" article',           'todo',       'medium',   'Feature',     'Career',      t(30),    past_ts(3),  past_ts(3)),
    ]
    cur.executemany(
        'INSERT OR REPLACE INTO tasks '
        '(task_id,project_id,sprint_id,parent_task_id,title,description,status,priority,label,category,due_date,created_at,updated_at) '
        'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
        tasks
    )

    # ── COMMENTS ─────────────────────────────────────────────────────────────
    comments = [
        (1,  6,  'MDX rendering looks great on desktop — need to check mobile wrapping.',    past_ts(3,10)),
        (2,  6,  'rehype-pretty-code is much better than prism for this use case.',          past_ts(2,14)),
        (3,  7,  'Using next-themes for dark mode — super clean API.',                       past_ts(1,9)),
        (4,  19, 'Hit 80 kg today — up from 75 kg starting weight. Feeling strong!',        past_ts(4,8)),
        (5,  20, 'MyFitnessPal API works well for auto-logging.',                            past_ts(2,11)),
        (6,  25, 'Spent way too much on takeaways last week — need to be strict.',           past_ts(3,12)),
        (7,  27, 'Standing order set up for the 25th — just need to confirm amount.',        past_ts(1,16)),
        (8,  39, 'First epoch loss: 1.87 — looks healthy so far.',                          past_ts(0,17)),
        (9,  39, 'GPU utilisation at 94% — good. ETA ~6 hours for full run.',               past_ts(0,19)),
        (10, 47, 'Deepmind and Wayve both look very promising — added to shortlist.',        past_ts(1,10)),
        (11, 48, 'Finished "Designing Data-Intensive Applications" chapter 5.',              past_ts(2,20)),
        (12, 46, 'LinkedIn connections up 12% after updating headline and banner.',          past_ts(6,15)),
    ]
    cur.executemany(
        'INSERT OR REPLACE INTO task_comments (comment_id,task_id,content,created_at) VALUES (?,?,?,?)',
        comments
    )

    # ── EVENTS ───────────────────────────────────────────────────────────────
    events = [
        # id, project_id, title, description, location, on_date, on_time, created_at, updated_at
        (1,  1, 'Portfolio launch',           'Go live on custom domain',                        'vercel.app',           t(14),     '10:00', past_ts(10), past_ts(10)),
        (2,  1, 'Design review with friend',  'Get feedback on layout and copy',                 'Google Meet',          t(3),      '18:30', past_ts(8),  past_ts(8)),
        (3,  2, 'Gym PT session',             'Assessment and programme design with trainer',    'PureGym City Centre',  t(2),      '07:00', past_ts(5),  past_ts(5)),
        (4,  2, 'Weigh-in & measurements',    'Monthly progress photos and measurements',        'Home',                 t(7),      '08:00', past_ts(5),  past_ts(5)),
        (5,  3, 'Monthly budget review',      'Sit down and review April vs targets',            'Home',                 t(12),     '19:00', past_ts(7),  past_ts(7)),
        (6,  3, 'ISA transfer deadline',      'Annual ISA allowance resets',                     'Monzo app',            t(5),      '23:59', past_ts(6),  past_ts(6)),
        (7,  4, 'Supervisor meeting',         'Progress update on model training results',       'Room 4.12, CS Dept',   t(4),      '14:00', past_ts(9),  past_ts(9)),
        (8,  4, 'Dissertation deadline',      'Final PDF submission via university portal',      'Online portal',        t(60),     '17:00', past_ts(30), past_ts(30)),
        (9,  4, 'Peer review session',        'Exchange drafts with study group',               'Library Study Room 3', t(9),      '13:00', past_ts(4),  past_ts(4)),
        (10, 5, 'Technical interview – Wayve','On-site system design + coding round',           'Wayve HQ, London',     t(12),     '10:00', past_ts(3),  past_ts(3)),
        (11, 5, 'Coffee chat – ex-colleague', 'Informal catch-up, ask about openings',          'Pret a Manger, EC2',   t(6),      '12:30', past_ts(2),  past_ts(2)),
        (12, 5, 'Final round – Monzo',        'Values interview + take-home review',            'Monzo HQ, London',     t(18),     '09:30', past_ts(1),  past_ts(1)),
    ]
    cur.executemany(
        'INSERT OR REPLACE INTO events (event_id,project_id,title,description,location,on_date,on_time,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)',
        events
    )

    # ── ACTIVITY LOG ─────────────────────────────────────────────────────────
    log = [
        (1,  1, None, 'project_created',      'Project "Portfolio Website" created',                       past_ts(40)),
        (2,  2, None, 'project_created',      'Project "Fitness & Nutrition" created',                     past_ts(30)),
        (3,  3, None, 'project_created',      'Project "Budget Planner 2026" created',                     past_ts(20)),
        (4,  4, None, 'project_created',      'Project "Machine Learning BSc" created',                    past_ts(60)),
        (5,  5, None, 'project_created',      'Project "Career Growth" created',                           past_ts(15)),
        (6,  1, None, 'sprint_created',       'Sprint "Sprint 1 – Foundation" created',                    past_ts(30)),
        (7,  1, None, 'sprint_started',       'Sprint "Sprint 1 – Foundation" started',                    past_ts(28)),
        (8,  1, None, 'sprint_completed',     'Sprint "Sprint 1 – Foundation" completed — 4/4 tasks done', past_ts(15,18)),
        (9,  1, None, 'sprint_created',       'Sprint "Sprint 2 – Content" created',                       past_ts(15)),
        (10, 1, None, 'sprint_started',       'Sprint "Sprint 2 – Content" started',                       past_ts(14)),
        (11, 1, 1,    'task_created',         'Task "Initialise Next.js repo" created',                    past_ts(28)),
        (12, 1, 1,    'task_moved',           'Task "Initialise Next.js repo" moved to done',              past_ts(18)),
        (13, 1, 5,    'task_moved',           'Task "Projects showcase page" moved to done',               past_ts(5)),
        (14, 4, None, 'sprint_completed',     'Sprint "Literature Review" completed — 4/4 tasks done',     past_ts(20,17)),
        (15, 4, 37,   'task_created',         'Task "Preprocess dataset" created',                         past_ts(18)),
        (16, 4, 37,   'task_moved',           'Task "Preprocess dataset" moved to done',                   past_ts(10,17)),
        (17, 4, 38,   'task_moved',           'Task "Implement baseline CNN" moved to done',               past_ts(5,20)),
        (18, 4, 39,   'task_moved',           'Task "Train on GPU cluster" moved to inprogress',           past_ts(0,16)),
        (19, 5, 46,   'task_moved',           'Task "Update CV and LinkedIn" moved to done',               past_ts(7,11)),
        (20, 5, 51,   'task_moved',           'Task "Research target companies" moved to done',            past_ts(5,14)),
        (21, 3, 23,   'task_moved',           'Task "Categorise all March expenses" moved to done',        past_ts(10,16)),
        (22, 3, 24,   'task_moved',           'Task "Set April budget limits" moved to done',              past_ts(8,12)),
        (23, 2, 15,   'task_moved',           'Task "Log starting measurements" moved to done',            past_ts(20)),
        (24, 2, 18,   'task_moved',           'Task "5-day workout streak" moved to done',                 past_ts(8,18)),
        (25, 1, 6,    'comment_added',        'Comment added to task',                                     past_ts(3,10)),
        (26, 4, 39,   'comment_added',        'Comment added to task',                                     past_ts(0,17)),
        (27, 5, 10,   'event_created',        'Event "Technical interview – Wayve" created',               past_ts(3)),
        (28, 1, 1,    'event_created',        'Event "Portfolio launch" created',                          past_ts(10)),
    ]
    cur.executemany(
        'INSERT OR REPLACE INTO activity_log (log_id,project_id,task_id,action,details,timestamp) VALUES (?,?,?,?,?,?)',
        log
    )

    conn.commit()
    conn.close()

    print("✓ Demo data inserted successfully!")
    print("  5 projects | 11 sprints | 56 tasks (incl. subtasks) | 12 comments | 12 events | 28 activity logs")

if __name__ == '__main__':
    run()
