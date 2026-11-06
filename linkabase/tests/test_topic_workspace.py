"""Topic-scoped navigation, default embedded drawing, and scope reset checks."""
import _bootstrap
import os,tempfile
from unittest.mock import patch
os.environ['WORKSPACE_DIR']=tempfile.mkdtemp()
from store import init,save_doc,digest,new_diagram,execute
from auth import init_auth,create_user,login
from notes import init_notes,create_note,add_child
from projects import create_project
from streamlit.testing.v1 import AppTest
init();init_auth();init_notes()
owner=create_user('Owner','owner@example.com','password-12345',bootstrap=True)
token=login('owner@example.com','password-12345')
create_project(token,'First','FIRST');create_project(token,'Second','SECOND')
a=create_note(token,'FIRST','Topic A');b=create_note(token,'FIRST','Topic B')
for topic,name in [(a,'Alpha'),(b,'Beta')]:
 save_doc('FIRST/'+name+'.md','# '+name,digest(''))
 add_child(token,'FIRST',topic,'doc','FIRST/'+name+'.md',name+' wiki')
drawing=new_diagram('FIRST','Alpha drawing')
child=add_child(token,'FIRST',a,'diagram',drawing,'Alpha drawing')
ui=AppTest.from_file(str(_bootstrap.PROJECT/'src/app.py'),default_timeout=30)
ui.session_state.token=token;ui.run();assert not ui.exception
next(s for s in ui.sidebar.selectbox if s.label=='Library topic').set_value(a).run()
with patch('surface.render_surface',return_value=None) as surface:
 next(x for x in ui.sidebar.button if x.label=='Wiki').click().run()
 assert not ui.exception
 markup=surface.call_args.args[0]
 assert 'Alpha wiki' in markup and 'Beta wiki' not in markup
 assert not any(s.label=='Parent topic' for s in ui.selectbox)
next(x for x in ui.sidebar.button if x.label=='Diagrams').click().run()
with patch('surface.render_surface',side_effect=[{'kind':'open','id':child},None]):ui.run()
assert not ui.exception
assert len(ui.get('iframe'))==1
assert '/editor/'+drawing in ui.get('iframe')[0].proto.src
assert not any(c.label=='Edit here' for c in ui.checkbox)
mode=next(g for g in ui.get('button_group') if g.label=='Diagram view')
assert mode.value=='Editor'
mode.set_value('Preview').run();assert not ui.exception
assert not ui.get('iframe')
assert any('No saved preview yet' in item.value for item in ui.info)
next(g for g in ui.get('button_group') if g.label=='Diagram view').set_value('Editor').run()
assert not ui.exception and ui.get('iframe')
# Changing topic clears the full reader; no cross-topic drawing is kept open.
with patch('surface.render_surface',return_value=None) as surface:
 next(s for s in ui.sidebar.selectbox if s.label=='Library topic').set_value(b).run()
 assert not ui.exception and not ui.get('iframe')
 assert 'Alpha drawing' not in surface.call_args.args[0]
 assert 'library_full' not in ui.session_state
# Returning to all topics restores the complete library.
with patch('surface.render_surface',return_value=None) as surface:
 next(x for x in ui.sidebar.button if x.label=='Wiki').click().run()
 next(s for s in ui.sidebar.selectbox if s.label=='Library topic').set_value('').run()
 assert 'Alpha wiki' in surface.call_args.args[0] and 'Beta wiki' in surface.call_args.args[0]
# Topic selection never leaks across projects.
next(s for s in ui.sidebar.selectbox if s.label=='Project').set_value('SECOND').run()
assert not ui.exception
assert next(s for s in ui.sidebar.selectbox if s.label=='Library topic').value==''
reader=create_user('Reader','reader@example.com','password-12345')
execute('INSERT INTO memberships VALUES (?,?,?)',(reader,'FIRST','read'))
reader_token=login('reader@example.com','password-12345')
read_ui=AppTest.from_file(str(_bootstrap.PROJECT/'src/app.py'),default_timeout=30)
read_ui.session_state.token=reader_token;read_ui.session_state.page='Diagrams'
read_ui.run();assert not read_ui.exception
with patch('surface.render_surface',side_effect=[{'kind':'open','id':child},None]):read_ui.run()
assert not read_ui.exception and read_ui.get('iframe')
assert any('Read-only drawing' in c.value for c in read_ui.caption)
read_ui.session_state.page='Topics';read_ui.session_state.selected_note=a;read_ui.session_state.selected_child=child
read_ui.run();assert not read_ui.exception
assert next(b for b in read_ui.sidebar.button if b.label=='Diagrams').proto.type=='primary'
assert next(b for b in read_ui.sidebar.button if b.label=='Topics').proto.type=='secondary'
print('PASS: topic scope, embedded editor/preview, reader mode, scope reset, all-topics and project isolation')
