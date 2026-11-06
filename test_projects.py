"""Fresh startup, project lifecycle, scope-specific forms and permissions."""
import os,tempfile,json
os.environ['WORKSPACE_DIR']=tempfile.mkdtemp()
from pathlib import Path
from unittest.mock import patch
from store import *
from auth import *
from notes import *
from projects import *
init();init_auth();init_notes();init()
assert not rows('SELECT * FROM projects')
owner=create_user('Owner','owner@example.com','owner-password-123',bootstrap=True);token=login('owner@example.com','owner-password-123')
reader=create_user('Reader','reader@example.com','reader-password-123');rt=login('reader@example.com','reader-password-123')
from streamlit.testing.v1 import AppTest
ui=AppTest.from_file('app.py',default_timeout=30);ui.session_state.token=token;ui.run();assert not ui.exception
assert not [x for x in ui.selectbox if x.label=='Project']
# First project through the empty-state form.
[x for x in ui.text_input if x.label=='Project name'][-1].set_value('First project')
[x for x in ui.text_input if x.label=='Project key'][-1].set_value('FIRST')
[x for x in ui.button if x.label=='Create project'][-1].click().run();assert not ui.exception
assert rows('SELECT name FROM projects WHERE id=?',('FIRST',))[0]['name']=='First project'
assert not rows('SELECT * FROM tasks') and not rows('SELECT * FROM notes')
node=create_note(token,'FIRST','First topic')
for page,button,kind,title_field in [('Wiki','Add Wiki','doc','Wiki title'),('Diagrams','Add Diagram','diagram','Diagram title'),('Storage','Add Storage','asset','Storage title')]:
 [x for x in ui.sidebar.button if x.label==page][0].click().run();assert not ui.exception
 [x for x in ui.button if x.label==button][0].click().run();assert not ui.exception
 assert not [x for x in ui.selectbox if x.label=='Content type']
 [x for x in ui.text_input if x.label==title_field][0].set_value('Scoped '+kind)
 if kind=='doc':[x for x in ui.text_area if x.label=='Markdown'][0].set_value('# Scoped wiki')
 if kind=='asset':
  [x for x in ui.radio if x.label=='Storage type'][0].set_value('External link')
  [x for x in ui.text_input if x.label=='HTTPS link'][0].set_value('https://example.com/storage')
 [x for x in ui.button if x.label==button][-1].click().run();assert not ui.exception
 assert children(token,'FIRST',node,kind)
# Generic add-content stays available inside Topics.
[x for x in ui.button if x.label=='Add content'][0].click().run();assert [x for x in ui.selectbox if x.label=='Content type']
ui.session_state['content_dialog']=None;ui.run()
# Rename through project settings, retaining identity and content.
[x for x in ui.sidebar.button if x.label=='Project settings'][0].click().run();assert not ui.exception
[x for x in ui.text_input if x.label=='Project name'][0].set_value('Renamed project')
[x for x in ui.button if x.label=='Save project name'][0].click().run();assert not ui.exception
assert rows('SELECT name FROM projects WHERE id=?',('FIRST',))[0]['name']=='Renamed project'
assert len(children(token,'FIRST'))==3
create_project(token,'Second project','SECOND');ref='FIRST/local.md';save_doc(ref,'old',digest(''));save_doc(ref,'new',digest('old'));local=add_child(token,'FIRST',node,'doc',ref,'Local wiki')
(ROOT/'attachments'/'private.txt').write_text('project file');execute('INSERT INTO assets VALUES (?,?,?,?,?,?)',('FILE','FIRST','File','attachments/private.txt',12,''))
execute('INSERT INTO memberships VALUES (?,?,?)',(reader,'FIRST','read'))
fields=dict(title='Project task',status='Ready',priority='Low',owner='',due='',description='')
save_task(token,'FIRST','FIRST-TASK',fields,'note:'+node,assignee=owner)
for action in [lambda:rename_project(rt,'FIRST','Denied'),lambda:delete_project(rt,'FIRST'),lambda:create_project(rt,'Denied','DENIED')]:
 try:action();raise AssertionError('Reader admin action allowed')
 except PermissionError:pass
delegated=create_user('Project admin','admin@example.com','project-admin-123');execute('INSERT INTO memberships VALUES (?,?,?)',(delegated,'FIRST','admin'));dt=login('admin@example.com','project-admin-123')
rename_project(dt,'FIRST','Delegated rename')
try:delete_project(dt,'SECOND');raise AssertionError('Cross-project admin deletion allowed')
except PermissionError:pass
# Filesystem failure must restore all active rows and moved files.
original=Path.replace;calls=[0]
def fail_second(self,target):
 calls[0]+=1
 if calls[0]==2:raise OSError('simulated storage failure')
 return original(self,target)
try:
 with patch.object(Path,'replace',fail_second):delete_project(token,'FIRST')
 raise AssertionError('Expected storage failure')
except OSError:pass
assert rows('SELECT id FROM projects WHERE id=?',('FIRST',))
assert (ROOT/'docs'/ref).read_text()=='new'
# Delete through UI: key confirmation and Cancel.
[x for x in ui.button if x.label=='Delete project'][0].click().run();assert not ui.exception
[x for x in ui.button if x.label=='Delete project and contents'][0].click().run();assert not ui.exception
assert rows('SELECT id FROM projects WHERE id=?',('FIRST',))
assert ui.error
[x for x in ui.button if x.label=='Cancel'][0].click().run();assert not ui.exception
[x for x in ui.button if x.label=='Delete project'][0].click().run()
[x for x in ui.text_input if x.label=='Type the project key to confirm'][0].set_value('FIRST')
[x for x in ui.button if x.label=='Delete project and contents'][0].click().run();assert not ui.exception
assert not rows('SELECT id FROM projects WHERE id=?',('FIRST',))
for table in ['tasks','notes','note_children','diagrams','assets','memberships']:assert not rows('SELECT * FROM '+table+' WHERE project=?',('FIRST',))
assert not rows('SELECT * FROM task_targets WHERE task=?',('FIRST-TASK',))
assert not rows('SELECT * FROM task_assignees WHERE task=?',('FIRST-TASK',))
assert rows('SELECT id FROM projects WHERE id=?',('SECOND',))
assert user_for(token)['id']==owner and user_for(rt)['id']==reader
archive=rows("SELECT * FROM trash_entries WHERE kind='project'")[0]
assert (ROOT/'trash'/archive['id']/'docs'/ref).read_text()=='new'
assert json.loads(archive['payload'])['tables']['tasks']
delete_project(token,'SECOND');init();assert not rows('SELECT * FROM projects')
ui.run();assert not ui.exception
assert any(x.value=='Create your first project' for x in ui.title)
print('PASS: no demo seeding, empty-state creation, fixed content forms, generic topic form, rename, role checks, deletion/cancel, archive rollback, complete project cleanup, other projects/accounts retained, last-project deletion stays empty')
