"""Transfer controls are restricted and export only encrypted bytes."""
import _bootstrap
import os,tempfile
os.environ['WORKSPACE_DIR']=tempfile.mkdtemp()
from store import init,execute
from auth import init_auth,create_user,login
from notes import init_notes
from projects import create_project
from streamlit.testing.v1 import AppTest
init();init_auth();init_notes()
owner=create_user('Owner','owner@example.com','password-12345',bootstrap=True)
token=login('owner@example.com','password-12345');create_project(token,'Project','PROJ')
reader=create_user('Reader','reader@example.com','password-12345');execute('INSERT INTO memberships VALUES (?,?,?)',(reader,'PROJ','admin'))
reader_token=login('reader@example.com','password-12345')
ui=AppTest.from_file(str(_bootstrap.PROJECT/'src/app.py'),default_timeout=30)
ui.session_state.token=token;ui.run()
next(b for b in ui.sidebar.button if b.label=='Project transfers').click().run()
assert not ui.exception and ui.title[0].value=='Project transfers'
next(t for t in ui.text_input if t.label=='Archive password').set_value('archive-password-12345')
next(t for t in ui.text_input if t.label=='Confirm archive password').set_value('archive-password-12345')
next(b for b in ui.button if b.label=='Create encrypted export').click().run()
assert not ui.exception and ui.session_state.project_export['data'].startswith(b'LINKABASE-PROJECT')
assert 'archive-password-12345' not in repr(ui.session_state.project_export)
restricted=AppTest.from_file(str(_bootstrap.PROJECT/'src/app.py'),default_timeout=30)
restricted.session_state.token=reader_token;restricted.run()
assert not any(b.label=='Project transfers' for b in restricted.sidebar.button)
restricted.session_state.page='Transfers';restricted.run()
assert not restricted.exception and restricted.error
assert not restricted.get('file_uploader')
print('PASS: encrypted export UI and denied forged access for project admins')
