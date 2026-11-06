"""An actionable project overview using existing tasks and workspace content."""
from datetime import date
from html import escape
import streamlit as st
from store import rows
from notes import KINDS, project_users
from ui import item_label


def assigned_tasks(token, user, project, tasks):
    """Resolve ID assignments first; accept legacy names only when unambiguous."""
    assignments = {r['task']: r['user'] for r in rows(
        'SELECT a.task,a.user FROM task_assignees a JOIN tasks t ON t.id=a.task WHERE t.project=?',
        (project,))}
    unique_name = sum(person['name'] == user['name'] for person in project_users(token, project)) == 1
    mine = [task for task in tasks if task['status'] != 'Done' and (
        assignments.get(task['id']) == user['id'] or
        (task['id'] not in assignments and unique_name and task['owner'] == user['name']))]
    priorities = {'High': 0, 'Medium': 1, 'Low': 2}
    return sorted(mine, key=lambda task: (
        not bool(task['due']), task['due'], priorities.get(task['priority'], 3), task['id']))


def overview_markup(user, details, tasks, mine, notes, content, targets, labels):
    """Render real project information using the HTML concept's exact layout."""
    from surface import action, initials
    done = sum(t['status'] == 'Done' for t in tasks)
    summary = (f'<section class="panel project-summary"><div class="summary-text"><h2>{escape(details["name"])} '
               '<span class="tag blue" style="margin-left:8px">Active project</span></h2>'
               f'<p>{escape(details["description"] or "Tasks, knowledge, and diagrams for this project.")}</p></div>'
               '<div class="progress-box"><div class="progress-caption"><span>Project progress</span>'
               f'<strong>{done} / {len(tasks)} tasks</strong></div><div class="bar"><span style="width:{done/max(len(tasks),1)*100:.0f}%"></span></div>'
               f'<span>{done/max(len(tasks),1):.0%} complete</span></div></section>')
    today = date.today().isoformat()
    due_count = sum(t['due'] == today for t in mine)
    stats = [('Assigned to you', len(mine), f'{due_count} due today'),
             ('In progress', sum(t['status'] == 'In progress' for t in tasks), 'Across the project'),
             ('Needs review', sum(t['status'] == 'Review' for t in tasks), 'Ready for feedback'),
             ('Completed', done, 'Across the project')]
    metrics = '<div class="metrics">' + ''.join(
        f'<div class="panel metric"><div class="metric-top">{label}</div><strong>{count:02d}</strong><small>{detail}</small></div>'
        for label, count, detail in stats) + '</div>'
    focus = '<section class="panel"><div class="panel-head"><h2>Your next tasks</h2>' + action('All tasks →', 'page', 'Tasks') + '</div>'
    for task in mine[:5]:
        due = ('Overdue · ' + task['due']) if task['due'] and task['due'] < today else (
            'Due today' if task['due'] == today else task['due'] or task['status'])
        linked = labels.get(targets.get(task['id'], ''), 'No linked topic')
        inner = ('<span class="check"></span><div class="grow"><div class="row-title">' + escape(task['title']) +
                 '</div><div class="row-sub">' + escape(task['id'] + ' · ' + linked) + '</div></div>' +
                 '<span class="tag ' + ('peach' if task['due'] and task['due'] <= today else 'blue') + '">' +
                 escape(due) + '</span><span class="avatar">' + initials(user['name']) + '</span>')
        focus += action(task['title'], 'task', task['id'], 'row', inner)
    if not mine: focus += '<div class="empty"><strong>You’re all caught up.</strong>No open tasks assigned to you. Browse the board to see the project’s work.</div>'
    focus += '<div class="row-note">Ordered by due date, then priority.</div></section>'
    topics = '<section class="panel"><div class="panel-head"><h2>Project topics</h2>' + action('All topics →', 'page', 'Topics') + '</div>'
    for note in notes[:4]:
        inner = ('<span class="topic-icon">▱</span><div class="grow"><div class="row-title">' + escape(note['title']) +
                 '</div><div class="row-sub">' + str(note['child_count']) + ' connected items</div></div><span class="muted">→</span>')
        topics += action(note['title'], 'topic', note['id'], 'row', inner)
    if not notes: topics += '<div class="empty"><strong>Give your knowledge a home.</strong>Create a topic to collect related pages and drawings.</div>'
    topics += '</section>'
    content_panel = '<section class="panel full"><div class="panel-head"><h2>Project content</h2>' + action('Browse wiki →', 'page', 'Wiki') + '</div>'
    content_panel += '<div class="recent-row header"><span>Name</span><span>Topic</span><span>Type</span></div>'
    topic_names = {n['id']:n['title'] for n in notes}
    symbols = {'doc':'▤', 'diagram':'◇'}
    for child in sorted(content, key=lambda c:c['title'].casefold())[:5]:
        inner = ('<span class="recent-title"><span class="topic-icon">' + symbols[child['kind']] +
                 '</span><strong>' + escape(child['title']) + '</strong></span><span>' +
                 escape(topic_names.get(child['note'], 'Topic')) + '</span><span>' + escape(KINDS[child['kind']]) + '</span>')
        content_panel += action(child['title'], 'content', child['id'], 'recent-row', inner)
    if not content: content_panel += '<div class="empty"><strong>A clean slate.</strong>Add a wiki page or diagram to a topic to see it here.</div>'
    content_panel += '</section>'
    shortcuts = '<section class="overview-links">'
    for page, symbol, detail in [('Topics','▱','Knowledge, grouped by subject'),('Diagrams','◇','Architecture, flows, and visual notes'),('Wiki','▤','Decisions, plans, and project knowledge')]:
        inner = f'<span class="topic-icon">{symbol}</span><span><strong>{page}</strong><small>{detail}</small></span><span style="margin-left:auto;color:var(--muted)">→</span>'
        shortcuts += action(page, 'page', page, 'panel quick-link', inner)
    shortcuts += '</section>'
    return summary + metrics + '<div class="grid">' + focus + topics + content_panel + '</div>' + shortcuts


def render_overview(token, user, project, details, tasks, notes, content, targets, labels, go):
    from surface import render_surface
    st.caption('Your tasks, documents, and project activity in one place.')
    mine = assigned_tasks(token, user, project, tasks)
    event = render_surface(overview_markup(user, details, tasks, mine, notes, content, targets, labels),
                           key='project-overview:' + project, theme=user['theme'])
    if not isinstance(event, dict): return
    kind, id = event.get('kind'), event.get('id')
    if kind == 'task' and id in {t['id'] for t in tasks}:
        st.session_state.open_task = id
    elif kind == 'page' and id in {'Tasks','Topics','Wiki','Diagrams'}:
        go(id); st.rerun()
    elif kind == 'topic' and id in {n['id'] for n in notes}:
        go('Topics', note=id); st.rerun()
    elif kind == 'content':
        child = next((c for c in content if c['id'] == id), None)
        if child:
            go('Topics', note=child['note'], child=id); st.rerun()
