"""Topic-only task links, legacy conversion, and content lifecycle behavior."""
import _bootstrap
import os
import tempfile
os.environ['WORKSPACE_DIR'] = tempfile.mkdtemp()
from store import init, execute, rows, save_doc, digest, new_diagram
from auth import init_auth, create_user, login
from notes import (init_notes, create_note, add_child, save_task, task_targets,
                   target_choices, move_child, delete_content, sync_project)
from projects import create_project
from streamlit.testing.v1 import AppTest

init(); init_auth(); init_notes()
owner = create_user('Owner', 'owner@example.com', 'password-12345', bootstrap=True)
token = login('owner@example.com', 'password-12345')
create_project(token, 'Project One', 'ONE'); create_project(token, 'Project Two', 'TWO')
topic = create_note(token, 'ONE', 'Planning')
other = create_note(token, 'ONE', 'Delivery')
foreign = create_note(token, 'TWO', 'Private')
save_doc('ONE/Plan.md', '# Plan', digest(''))
doc = add_child(token, 'ONE', topic, 'doc', 'ONE/Plan.md', 'Plan')
diagram = new_diagram('ONE', 'Map')
drawing = add_child(token, 'ONE', topic, 'diagram', diagram, 'Map')
fields = dict(title='A task', status='Ready', priority='Medium', owner='', due='', description='')
for task, child in [('DOC', doc), ('DRAWING', drawing)]:
    save_task(token, 'ONE', task, fields)
    execute('INSERT INTO task_targets VALUES (?,?,?)', (task, 'child', child))
save_task(token, 'ONE', 'BROKEN', fields)
execute('INSERT INTO task_targets VALUES (?,?,?)', ('BROKEN', 'child', 'missing'))
init_notes(); init_notes()
assert task_targets('ONE') == {task: 'note:' + topic for task in ['DOC', 'DRAWING']}
assert not rows("SELECT * FROM task_targets WHERE target_type='child'")
assert rows('SELECT id FROM tasks WHERE id=?', ('BROKEN',))
save_task(token, 'ONE', 'LEGACY', fields)
execute('UPDATE tasks SET doc=? WHERE id=?', ('ONE/Plan.md', 'LEGACY'))
sync_project('ONE'); sync_project('ONE')
assert task_targets('ONE')['LEGACY'] == 'note:' + topic
assert set(target_choices(token, 'ONE')) == {'', 'note:' + topic, 'note:' + other}
for invalid in ['child:' + doc, 'diagram:' + diagram, 'note:' + foreign, 'note:missing', 'note:', 'invalid']:
    try:
        save_task(token, 'ONE', 'DOC', dict(fields, title='Should not save'), invalid)
        raise AssertionError('Invalid link accepted: ' + invalid)
    except ValueError:
        pass
    assert rows('SELECT title FROM tasks WHERE id=?', ('DOC',))[0]['title'] == 'A task'
    assert task_targets('ONE')['DOC'] == 'note:' + topic
move_child(token, 'ONE', doc, other)
assert task_targets('ONE')['DOC'] == 'note:' + topic
delete_content(token, 'ONE', drawing)
assert task_targets('ONE')['DRAWING'] == 'note:' + topic

ui = AppTest.from_file(str(_bootstrap.PROJECT / 'src' / 'app.py'), default_timeout=30)
ui.session_state.token = token; ui.session_state.page = 'Tasks'
ui.run(); assert not ui.exception
next(b for b in ui.button if b.label == 'New task').click().run()
picker = next(s for s in ui.selectbox if s.label == 'Linked topic')
assert set(picker.options) == {'No linked topic', 'Topic · Planning', 'Topic · Delivery'}
next(t for t in ui.text_input if t.label == 'Title').set_value('Topic-only task')
picker.set_value('note:' + other)
next(b for b in ui.button if b.label == 'Save task').click().run(); assert not ui.exception
created = rows('SELECT id FROM tasks WHERE title=?', ('Topic-only task',))[0]['id']
assert task_targets('ONE')[created] == 'note:' + other
save_task(token, 'ONE', 'UNLINK', fields, 'note:'+other)
save_task(token, 'ONE', 'UNLINK', fields, '')
assert 'UNLINK' not in task_targets('ONE')
delete_content(token, 'ONE', topic, whole_base=True)
assert all(task not in task_targets('ONE') for task in ['DOC', 'DRAWING', 'LEGACY'])
assert len(rows("SELECT id FROM tasks WHERE id IN ('DOC','DRAWING','LEGACY')")) == 3
assert task_targets('ONE')[created] == 'note:' + other
print('PASS: topic-only validation, legacy migration, UI choices, unlinking, content movement/deletion, task retention')
