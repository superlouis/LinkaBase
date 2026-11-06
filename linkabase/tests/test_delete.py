import _bootstrap
import os,tempfile,json
os.environ['WORKSPACE_DIR']=tempfile.mkdtemp()
from pathlib import Path
from unittest.mock import patch
from store import *
from auth import *
from notes import *
init();
from test_fixtures import seed_projects
seed_projects();init_auth();init_notes()
owner=create_user('Owner','owner@example.com','owner-password-123',bootstrap=True);token=login('owner@example.com','owner-password-123')
r=create_user('Read','read@example.com','reader-password-123');execute('INSERT INTO memberships VALUES (?,?,?)',(r,'PLAT','read'));rt=login('read@example.com','reader-password-123')
sync_project('PLAT');base=create_note(token,'PLAT','Delete test')
ref='PLAT/deletion.md';save_doc(ref,'old',digest(''));save_doc(ref,'new',digest('old'));doc=add_child(token,'PLAT',base,'doc',ref,'Document')
diagram=new_diagram('PLAT','Diagram');execute('UPDATE diagrams SET preview=? WHERE id=?',(b'example bytes',diagram));(ROOT/'diagrams'/f'{diagram}.excalidraw').write_text('{}');dia=add_child(token,'PLAT',base,'diagram',diagram,'Diagram')
f=dict(title='Retain task',status='Ready',priority='High',owner='',due='',description='')
for id,target in [('BASE-LINK','note:'+base),('DOC-LINK','note:'+base),('DIA-LINK','note:'+base)]:save_task(token,'PLAT',id,f,target)
try:delete_content(rt,'PLAT',doc);raise AssertionError('Reader deletion allowed')
except PermissionError:pass
try:delete_content(token,'RES',base,True);raise AssertionError('Cross project deletion allowed')
except ValueError:pass
# Simulate a filesystem failure after the first archive move, verify rollback.
original=Path.replace;count=[0]
def fail_second(self,target):
 count[0]+=1
 if count[0]==2:raise OSError('simulated move failure')
 return original(self,target)
try:
 with patch.object(Path,'replace',fail_second):delete_content(token,'PLAT',doc)
 raise AssertionError('Expected failure')
except OSError:pass
assert (ROOT/'docs'/ref).read_text()=='new'
assert any(c['id']==doc for c in children(token,'PLAT',base))
archive=delete_content(token,'PLAT',doc)
assert not (ROOT/'docs'/ref).exists()
assert (ROOT/'trash'/archive/'docs'/ref).read_text()=='new'
assert task_targets('PLAT')['DOC-LINK']=='note:'+base
assert rows('SELECT id FROM tasks WHERE id=?',('DOC-LINK',))
sync_project('PLAT');assert not any(c['id']==doc for c in children(token,'PLAT'))
archive=delete_content(token,'PLAT',base,True)
assert not children(token,'PLAT',base)
assert not rows('SELECT * FROM diagrams WHERE id=?',(diagram,))
assert len(rows("SELECT id FROM tasks WHERE id IN ('BASE-LINK','DOC-LINK','DIA-LINK')"))==3
assert not any(id in task_targets('PLAT') for id in ['BASE-LINK','DOC-LINK','DIA-LINK'])
assert json.loads((ROOT/'trash'/archive/'manifest.json').read_text())['children']
# Delete imported library. It must not be regenerated when other assigned content exists.
sibling=create_note(token,'PLAT','Keep me');save_doc('PLAT/keep.md','keep',digest(''));add_child(token,'PLAT',sibling,'doc','PLAT/keep.md','Keep')
delete_content(token,'PLAT','library:PLAT',True);sync_project('PLAT')
assert [b['id'] for b in list_notes(token,'PLAT')]==[sibling]
from streamlit.testing.v1 import AppTest
ui=AppTest.from_file(str(_bootstrap.PROJECT / 'src' / 'app.py'),default_timeout=30);ui.session_state['token']=token;ui.run()
[b for b in ui.sidebar.button if b.label=='Topics'][0].click().run();assert not ui.exception
with patch('surface.render_surface',side_effect=[{'kind':'topic','id':sibling},None]):ui.run()
assert not ui.exception
assert not [b for b in ui.button if b.label in ['Create task','Create task for this content']]
[b for b in ui.button if b.label=='Delete content'][0].click().run();assert not ui.exception
[b for b in ui.button if b.label=='Cancel'][0].click().run();assert not ui.exception
assert children(token,'PLAT',sibling)
[b for b in ui.button if b.label=='Delete content'][0].click().run()
[b for b in ui.button if b.label=='Delete content'][-1].click().run();assert not ui.exception
assert not children(token,'PLAT',sibling)
[b for b in ui.button if b.label=='Delete topic'][0].click().run();assert not ui.exception
[b for b in ui.button if b.label=='Delete topic and contents'][0].click().run();assert not ui.exception
assert not list_notes(token,'PLAT')
print('PASS: child/base deletion, archive, rollback, task retention/unlinking, access checks, default-base resurrection prevention, delete/cancel dialogs, no base task creation')
