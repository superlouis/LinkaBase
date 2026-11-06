"""Removing Storage preserves legacy data and leaves only wiki/diagram content."""
import _bootstrap
import os,tempfile,json,tomllib
from unittest.mock import patch
os.environ['WORKSPACE_DIR']=tempfile.mkdtemp()
from store import init,execute,rows,ROOT,save_doc,digest
from auth import init_auth,create_user,login
from notes import init_notes,create_note,add_child,children,list_notes,task_targets,save_task,KINDS
from projects import create_project,project_counts
from streamlit.testing.v1 import AppTest

init();init_auth();init_notes()
assert not rows("SELECT name FROM sqlite_master WHERE name='assets'")
assert not (ROOT/'attachments').exists()
owner=create_user('Owner','owner@example.com','password-12345',bootstrap=True)
token=login('owner@example.com','password-12345')
create_project(token,'Project','TEST')
topic=create_note(token,'TEST','Keep this topic')
save_doc('TEST/Keep.md','# Keep this document',digest(''))
doc=add_child(token,'TEST',topic,'doc','TEST/Keep.md','Keep this document')
# Simulate a workspace created by a previous release, including a legacy task link.
execute('CREATE TABLE assets(id TEXT PRIMARY KEY,project TEXT,name TEXT,path TEXT,size INTEGER,task TEXT)')
(ROOT/'attachments').mkdir()
upload=ROOT/'attachments/keep.txt';upload.write_text('Preserve this old upload')
execute('INSERT INTO assets VALUES (?,?,?,?,?,?)',('old-upload','TEST','Old upload','attachments/keep.txt',24,''))
execute('INSERT INTO assets VALUES (?,?,?,?,?,?)',('old-link','TEST','Old link','https://example.com/reference',0,''))
execute('INSERT INTO note_children VALUES (?,?,?,?,?,?)',('old-child',topic,'TEST','asset','old-upload','Old upload'))
fields=dict(title='Preserve task',status='Ready',priority='Medium',owner='',due='',description='')
save_task(token,'TEST','TASK',fields)
execute('INSERT INTO task_targets VALUES (?,?,?)',('TASK','child','old-child'))
# Failed archival must roll back schema, metadata, and task-link changes together.
with patch('migrations.json.dumps',side_effect=OSError('Simulated archive failure')):
    try:init_notes();raise AssertionError('Expected archive failure')
    except OSError:pass
assert rows("SELECT name FROM sqlite_master WHERE name='assets'")
assert rows("SELECT * FROM note_children WHERE id='old-child'")
assert rows("SELECT target_type FROM task_targets WHERE task='TASK'")[0]['target_type']=='child'
init_notes();init_notes()
assert not rows("SELECT name FROM sqlite_master WHERE name='assets'")
assert not rows("SELECT * FROM note_children WHERE kind='asset'")
archives=rows("SELECT * FROM trash_entries WHERE kind='retired_storage'")
assert len(archives)==1
payload=json.loads(archives[0]['payload'])
assert {a['id'] for a in payload['assets']}=={'old-upload','old-link'}
assert payload['children'][0]['id']=='old-child'
assert upload.read_text()=='Preserve this old upload'
assert task_targets('TEST')['TASK']=='note:'+topic
assert {c['id'] for c in children(token,'TEST')}=={doc}
assert list_notes(token,'TEST')[0]['child_count']==1
assert set(project_counts(token,'TEST'))=={'tasks','topics','drawings'}
try:add_child(token,'TEST',topic,'asset','old-upload','Rejected');raise AssertionError('Removed content type accepted')
except ValueError:pass
assert set(KINDS)=={'doc','diagram'}
with (_bootstrap.PROJECT/'pyproject.toml').open('rb') as source:
    assert not any('streamlit-pdf' in d.lower() or 'streamlit[pdf]' in d.lower() for d in tomllib.load(source)['project']['dependencies'])
ui=AppTest.from_file(str(_bootstrap.PROJECT/'src/app.py'),default_timeout=30)
ui.session_state.token=token;ui.session_state.page='Storage'
ui.run();assert not ui.exception and ui.session_state.page=='Highlight'
assert not any(b.label=='Storage' for b in ui.sidebar.button)
ui.session_state.page='Topics';ui.session_state.selected_note=topic;ui.session_state.content_dialog='asset'
ui.run();assert not ui.exception
assert next(s for s in ui.selectbox if s.label=='Content type').options==['Wiki page','Drawing']
assert not ui.get('file_uploader')
print('PASS: removed schema/UI/dependency, atomic legacy archival, preserved uploads/tasks/wiki, stale-session recovery')
