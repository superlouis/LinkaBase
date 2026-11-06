import _bootstrap
import os,tempfile
from datetime import date
os.environ['WORKSPACE_DIR']=tempfile.mkdtemp()
from store import *
from auth import *
from notes import *
init();
from test_fixtures import seed_projects
seed_projects();init_auth();init_notes()
admin=create_user('Owner','owner@example.com','owner-password-123',bootstrap=True);token=login('owner@example.com','owner-password-123')
alex=create_user('Alex','alex@example.com','alex-password-123');other=create_user('Alex','other@example.com','other-password-123');disabled=create_user('Disabled','disabled@example.com','disabled-password-123')
for id,project in [(alex,'PLAT'),(other,'RES'),(disabled,'PLAT')]:execute('INSERT INTO memberships VALUES (?,?,?)',(id,project,'write'))
execute('UPDATE users SET active=0 WHERE id=?',(disabled,))
assert {p['id'] for p in project_users(token,'PLAT')}=={admin,alex}
fields=dict(title='Assigned task',status='Ready',priority='High',owner='Ignored typed owner',due='2027-01-18',description='')
save_task(token,'PLAT','ASSIGN-TEST',fields,assignee=alex)
assert rows('SELECT owner,due FROM tasks WHERE id=?',('ASSIGN-TEST',))[0]==dict(owner='Alex',due='2027-01-18')
assert rows('SELECT user FROM task_assignees WHERE task=?',('ASSIGN-TEST',))[0]['user']==alex
for invalid in [other,disabled,'missing-user']:
 try:save_task(token,'PLAT','NO-TASK',fields,assignee=invalid);raise AssertionError('Invalid assignee allowed')
 except ValueError:pass
assert not rows('SELECT id FROM tasks WHERE id=?',('NO-TASK',))
from streamlit.testing.v1 import AppTest
ui=AppTest.from_file(str(_bootstrap.PROJECT / 'src' / 'app.py'),default_timeout=30);ui.session_state['token']=token;ui.session_state['page']='Tasks';ui.run();assert not ui.exception
[b for b in ui.button if b.label=='New task'][0].click().run();assert not ui.exception
assert not [t for t in ui.text_input if t.label=='Assignee' or 'Due date' in t.label]
[t for t in ui.text_input if t.label=='Title'][0].set_value('Calendar-selected task')
[s for s in ui.selectbox if s.label=='Assignee'][0].set_value(alex);ui.date_input[0].set_value(date(2027,2,15))
[b for b in ui.button if b.label=='Save task'][0].click().run();assert not ui.exception
created=rows('SELECT * FROM tasks WHERE title=?',('Calendar-selected task',))[0]
assert created['owner']=='Alex' and created['due']=='2027-02-15'
assert rows('SELECT user FROM task_assignees WHERE task=?',(created['id'],))[0]['user']==alex
[x for x in ui.radio if x.label=='View'][0].set_value('List').run();[b for b in ui.button if b.key==created['id']][0].click().run();assert not ui.exception
assert ui.date_input[0].value==date(2027,2,15)
assert [x for x in ui.selectbox if x.label=='Assignee'][0].value==alex
[x for x in ui.selectbox if x.label=='Assignee'][0].set_value('');ui.date_input[0].set_value(None)
[b for b in ui.button if b.label=='Save task'][0].click().run();assert not ui.exception
assert rows('SELECT owner,due FROM tasks WHERE id=?',(created['id'],))[0]==dict(owner='',due='')
assert not rows('SELECT user FROM task_assignees WHERE task=?',(created['id'],))
[b for b in ui.button if b.key=='PLAT-001'][0].click().run();assert not ui.exception
assert [x for x in ui.selectbox if x.label=='Assignee'][0].value=='__legacy__'
[b for b in ui.button if b.label=='Save task'][0].click().run();assert not ui.exception
assert rows('SELECT owner FROM tasks WHERE id=?',('PLAT-001',))[0]['owner']=='Steph-Yves'
print('PASS: active project users, assignee identity validation, dropdown/calendar creation, edit and clear, legacy preservation')
