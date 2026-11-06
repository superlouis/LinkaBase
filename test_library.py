import os,tempfile
os.environ['WORKSPACE_DIR']=tempfile.mkdtemp()
from store import *
from auth import *
from notes import *
from projects import create_project
from streamlit.testing.v1 import AppTest
init();init_auth();init_notes();create_user('Owner','owner@example.com','password-12345',bootstrap=True);t=login('owner@example.com','password-12345');create_project(t,'Library','LIB');n=create_note(t,'LIB','Handbook');save_doc('LIB/Start.md','# Start',digest(''));doc=add_child(t,'LIB',n,'doc','LIB/Start.md','Start here')
r=create_user('Reader','reader@example.com','password-12345');execute('INSERT INTO memberships VALUES (?,?,?)',(r,'LIB','read'));rt=login('reader@example.com','password-12345')
a=AppTest.from_file('app.py',default_timeout=30);a.session_state.token=rt;a.run()
next(b for b in a.sidebar.button if b.label=='Wiki').click().run();assert not a.exception
assert not [x for x in a.radio if x.label=='Documents']
next(b for b in a.button if b.label=='Start here').click().run();assert not a.exception
assert next(b for b in a.button if b.label=='Edit').disabled
next(b for b in a.button if b.label=='Full page').click().run();assert not a.exception
next(b for b in a.button if b.label=='Back to Wiki').click().run();assert not a.exception
next(b for b in a.sidebar.button if b.label=='Storage').click().run();assert not a.exception
assert 'library_open' not in a.session_state
print('PASS: reader library popup/full page, editing disabled, navigation')
