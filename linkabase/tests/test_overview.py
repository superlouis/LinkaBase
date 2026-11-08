"""Overview regression checks with real assignments and UI navigation."""
import _bootstrap
import os
import tempfile
os.environ['WORKSPACE_DIR'] = tempfile.mkdtemp()
from store import init, rows, execute, save_doc, digest
from auth import init_auth, create_user, login, user_for
from notes import init_notes, create_note, add_child, save_task
from projects import create_project
from overview import assigned_tasks, overview_markup
from notes import list_notes, children, task_targets, target_choices
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

init(); init_auth(); init_notes()
owner = create_user('Alex', 'alex@example.com', 'password-12345', bootstrap=True)
token = login('alex@example.com', 'password-12345')
assert user_for(token)['theme'] == 'Midnight'
create_project(token, 'Workspace <example>', 'WORK')
other = create_user('Alex', 'other@example.com', 'password-12345')
execute('INSERT INTO memberships VALUES (?,?,?)', (other, 'WORK', 'read'))
other_token = login('other@example.com', 'password-12345')
note = create_note(token, 'WORK', 'Product principles')
save_doc('WORK/Principles.md', '# Keep context close', digest(''))
child = add_child(token, 'WORK', note, 'doc', 'WORK/Principles.md', 'Principles')
for task_id, due, priority, assignee, status in [
    ('LATER', '2027-01-03', 'High', owner, 'Ready'),
    ('EARLY', '2027-01-01', 'Low', owner, 'Ready'),
    ('URGENT', '2027-01-01', 'High', owner, 'In progress'),
    ('UNDATED', '', 'High', owner, 'Ready'),
    ('OTHER', '2026-01-01', 'High', other, 'Ready'),
    ('DONE', '2026-01-01', 'High', owner, 'Done'),
]:
    save_task(token, 'WORK', task_id, dict(title=task_id, due=due, priority=priority,
              owner='', description='', status=status), target='note:' + note, assignee=assignee)
# Duplicate display names must never pull a legacy assignment into both dashboards.
save_task(token, 'WORK', 'LEGACY', dict(title='Legacy', due='', priority='Low',
          owner='Alex', description='', status='Ready'))
tasks = rows('SELECT * FROM tasks WHERE project=?', ('WORK',))
assert [t['id'] for t in assigned_tasks(token, user_for(token), 'WORK', tasks)] == [
    'URGENT', 'EARLY', 'LATER', 'UNDATED']

ui = AppTest.from_file(str(_bootstrap.PROJECT / 'src' / 'app.py'), default_timeout=30)
ui.session_state.token = token
ui.run(); assert not ui.exception
markup=overview_markup(user_for(token),rows('SELECT * FROM projects WHERE id=?',('WORK',))[0],tasks,assigned_tasks(token,user_for(token),'WORK',tasks),list_notes(token,'WORK'),children(token,'WORK'),task_targets('WORK'),target_choices(token,'WORK'))
assert 'Assigned to you' in markup and '<strong>04</strong>' in markup
assert 'Workspace &lt;example&gt;' in markup and 'Workspace <example>' not in markup
with patch('surface.render_surface',return_value={'kind':'task','id':'URGENT'}):ui.run()
assert not ui.exception
assert next(t for t in ui.text_input if t.label == 'Title').value == 'URGENT'
next(b for b in ui.sidebar.button if b.label == 'Overview').click().run()
with patch('surface.render_surface',side_effect=[{'kind':'content','id':child},None]):ui.run()
assert not ui.exception and ui.session_state.page == 'Topics'
assert ui.session_state.selected_note == note
assert any('Keep context close' in str(m.value) for m in ui.markdown)

reader = AppTest.from_file(str(_bootstrap.PROJECT / 'src' / 'app.py'), default_timeout=30)
reader.session_state.token = other_token
reader.run(); assert not reader.exception
assert len(assigned_tasks(other_token,user_for(other_token),'WORK',tasks))==1
assert next(b for b in reader.button if b.label == 'New task').disabled
with patch('surface.render_surface',return_value={'kind':'task','id':'OTHER'}):reader.run()
assert not reader.exception
assert not [b for b in reader.button if b.label == 'Save task']
print('PASS: assignment identity, due-date ordering, overview navigation, Midnight default, reader permissions')
