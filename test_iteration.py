"""uv run python test_iteration.py — isolated data, no existing workspace changes."""
import tempfile,os
os.environ['WORKSPACE_DIR']=tempfile.mkdtemp()
from store import *
from auth import *
from notes import *
init();
from test_fixtures import seed_projects
seed_projects();init_auth();init_notes()
a=create_user('Owner','owner@example.com','owner-password-123',bootstrap=True);token=login('owner@example.com','owner-password-123')
r=create_user('Reader','reader@example.com','reader-password-123');execute('INSERT INTO memberships VALUES (?,?,?)',(r,'PLAT','read'));rt=login('reader@example.com','reader-password-123')
sync_project('PLAT');sync_project('PLAT')
assert len(list_notes(token,'PLAT'))==1
assert len(children(token,'PLAT'))==1
assert len(task_targets('PLAT'))==5
note=create_note(token,'PLAT','Architecture','Connected design decisions')
other=create_note(token,'RES','Restricted research')
save_doc('PLAT/design.md','# Design',digest(''));cid=add_child(token,'PLAT',note,'doc','PLAT/design.md','Design')
second=new_diagram('PLAT','Architecture diagram');add_child(token,'PLAT',note,'diagram',second,'Architecture diagram')
fields=dict(title='Implement design',status='Ready',priority='High',owner='Owner',due='2026-12-01',description='Test task')
save_task(token,'PLAT','PLAT-TEST',fields,'child:'+cid)
try:save_task(token,'PLAT','PLAT-INVALID',fields,'note:'+other);raise AssertionError('Cross project target accepted')
except ValueError:pass
assert not rows('SELECT * FROM tasks WHERE id=?',('PLAT-INVALID',))
try:move_child(rt,'PLAT',cid,note);raise AssertionError('Reader write accepted')
except PermissionError:pass
try:add_child(token,'PLAT',other,'doc','PLAT/design.md','Design');raise AssertionError('Cross project child accepted')
except ValueError:pass
n2=create_note(token,'PLAT','New parent');move_child(token,'PLAT',cid,n2)
assert task_targets('PLAT')['PLAT-TEST']=='child:'+cid
assert children(token,'PLAT',n2)[0]['id']==cid
from streamlit.testing.v1 import AppTest
ui=AppTest.from_file('app.py',default_timeout=30);ui.session_state['token']=token;ui.run();assert not ui.exception
for label in ['Tasks','Topics','Wiki','Diagrams','Storage','My preferences','Workspace administration','Overview']:
 [b for b in ui.sidebar.button if b.label==label][0].click().run();assert not ui.exception,(label,ui.exception)
[b for b in ui.sidebar.button if b.label=='Topics'][0].click().run()
[b for b in ui.button if b.label=='New topic'][0].click().run()
assert not [x for x in ui.text_area if x.label=='Summary']
[t for t in ui.text_input if t.label=='Topic title'][0].set_value('Browser note')
[b for b in ui.button if b.label=='Save topic'][0].click().run();assert not ui.exception
new=next(n for n in list_notes(token,'PLAT') if n['title']=='Browser note')
assert ui.session_state.selected_note==new['id']
[b for b in ui.button if b.label=='Add content'][0].click().run();assert not ui.exception
[t for t in ui.text_input if t.label=='Content title'][0].set_value('Browser doc')
[t for t in ui.text_area if t.label=='Markdown'][-1].set_value('# Browser doc\nUseful notes.')
[b for b in ui.button if b.label=='Add to topic'][0].click().run();assert not ui.exception
child=children(token,'PLAT',new['id'])[0];assert child['title']=='Browser doc'
assert not [b for b in ui.button if b.label=='Create task']
[b for b in ui.sidebar.button if b.label=='Tasks'][0].click().run()
[b for b in ui.button if b.label=='New task'][0].click().run();assert not ui.exception
[t for t in ui.text_input if t.label=='Title'][0].set_value('Browser task')
[x for x in ui.selectbox if x.label=='Linked topic or child'][0].set_value('note:'+new['id'])
[b for b in ui.button if b.label=='Save task'][0].click().run();assert not ui.exception
created=rows('SELECT id FROM tasks WHERE title=?',('Browser task',))[0]
assert task_targets('PLAT')[created['id']]=='note:'+new['id']
[b for b in ui.sidebar.button if b.label=='My preferences'][0].click().run()
[s for s in ui.selectbox if s.label=='Theme'][0].set_value('Paper');[b for b in ui.button if b.label=='Apply theme'][0].click().run();assert not ui.exception
assert user_for(token)['theme']=='Paper'
ui=AppTest.from_file('app.py',default_timeout=30);ui.session_state['token']=rt;ui.run();assert not ui.exception
for page,label in [('Tasks','New task'),('Topics','New topic'),('Diagrams','Add Diagram')]:
 [b for b in ui.sidebar.button if b.label==page][0].click().run();assert not ui.exception
 assert [b for b in ui.button if b.label==label][0].disabled
assert not [b for b in ui.sidebar.button if b.label=='Workspace administration']
print('PASS: idempotent legacy import, note children, task targets, cross-project isolation, read-only access, moving content, grouped navigation, note/doc/task dialogs, theme preferences')
