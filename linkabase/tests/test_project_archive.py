"""Encrypted project round trips, privilege checks, and hostile/failed imports."""
import _bootstrap
import os,tempfile,json,io,zipfile,base64
from pathlib import Path
from unittest.mock import patch
os.environ['WORKSPACE_DIR']=tempfile.mkdtemp()
from store import init,save_doc,digest,new_diagram,execute,rows,ROOT
from auth import init_auth,create_user,login
from notes import init_notes,create_note,add_child,save_task,children,task_targets
from projects import create_project
import project_archive as archives
from project_archive import export_project,import_project
init();init_auth();init_notes()
owner=create_user('Alice','alice@example.com','password-12345',bootstrap=True)
token=login('alice@example.com','password-12345')
member=create_user('Bob','bob@example.com','password-12345');member_token=login('bob@example.com','password-12345')
create_project(token,'Original','ORIG','Private project');create_project(token,'Other','OTHER','Do not export')
execute('INSERT INTO memberships VALUES (?,?,?)',(member,'ORIG','admin'))
topic=create_note(token,'ORIG','Research')
save_doc('ORIG/Guide.md','# Original',digest(''),actor='Alice')
save_doc('ORIG/Guide.md','# Edited by Bob',digest('# Original'),actor='Bob')
add_child(token,'ORIG',topic,'doc','ORIG/Guide.md','Guide')
save_doc('ORIG/Loose.md','# Loose page',digest(''),actor='Alice')
diagram=new_diagram('ORIG','System map')
png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
execute('UPDATE diagrams SET preview=?,version=2 WHERE id=?',(png,diagram))
add_child(token,'ORIG',topic,'diagram',diagram,'System map')
fields=dict(title='Write guide',status='In progress',priority='High',owner='',due='2027-01-01',description='Keep the context')
save_task(token,'ORIG','TASK',fields,'note:'+topic,assignee=member)
password='archive-password-with-length'
for invalid_token in ['',member_token]:
 for operation in [lambda:export_project(invalid_token,'ORIG',password),lambda:import_project(invalid_token,b'anything',password,'NOPE')]:
  try:operation();raise AssertionError('Non-super-admin archive access allowed')
  except PermissionError:pass
blob=export_project(token,'ORIG',password)
assert b'Edited by Bob' not in blob and not zipfile.is_zipfile(io.BytesIO(blob))
assert export_project(token,'ORIG',password)!=blob
manifest,_=archives._read_archive(blob,password)
assert manifest['project']['id']=='ORIG'
assert not any(key in manifest for key in ['users','sessions','memberships','passwords'])
assert len(manifest['documents'])==2 and manifest['documents'][0]['history']
for bad in [blob[:-1]+bytes([blob[-1]^1]),b'not an archive']:
 try:import_project(token,bad,password,'BAD');raise AssertionError('Tampered archive accepted')
 except ValueError:pass
try:import_project(token,blob,'wrong-password-with-length','BAD');raise AssertionError('Wrong password accepted')
except ValueError:pass
import_project(token,blob,password,'COPY','Restored copy')
assert (ROOT/'docs/COPY/Guide.md').read_text()=='# Edited by Bob'
assert (ROOT/'docs/COPY/Loose.md').read_text()=='# Loose page'
new_topic=rows('SELECT id FROM notes WHERE project=?',('COPY',))[0]['id']
assert new_topic!=topic
new_task=rows('SELECT * FROM tasks WHERE project=?',('COPY',))[0]
assert new_task['id']!='TASK' and new_task['owner']=='Bob'
assert task_targets('COPY')[new_task['id']]=='note:'+new_topic
assert not rows('SELECT * FROM memberships WHERE project=?',('COPY',))
assert not rows('SELECT * FROM task_assignees WHERE task=?',(new_task['id'],))
assert len(rows('SELECT * FROM users'))==2
metadata=rows('SELECT * FROM wiki_authorship WHERE path=?',('COPY/Guide.md',))[0]
assert metadata['author']=='Alice' and metadata['last_editor']=='Bob'
new_diagram_row=rows('SELECT * FROM diagrams WHERE project=?',('COPY',))[0]
assert new_diagram_row['id']!=diagram and new_diagram_row['preview']==png and new_diagram_row['version']==2
assert (ROOT/'diagrams'/str(new_diagram_row['id']+'.excalidraw')).is_file()
import hashlib
history=ROOT/'history'/hashlib.sha256(b'COPY/Guide.md').hexdigest()
assert [p.read_text() for p in history.glob('*.md')]==['# Original']
try:import_project(token,blob,password,'COPY');raise AssertionError('Existing project overwritten')
except ValueError:pass
# A mid-move filesystem failure must roll back rows and every imported output.
original=Path.replace;count=[0]
def fail_second(self,target):
 count[0]+=1
 if count[0]==2:raise OSError('Simulated import write failure')
 return original(self,target)
with patch.object(Path,'replace',fail_second):
 try:import_project(token,blob,password,'ROLLBACK');raise AssertionError('Expected failure')
 except OSError:pass
assert not rows('SELECT * FROM projects WHERE id=?',('ROLLBACK',))
assert not (ROOT/'docs/ROLLBACK').exists()
assert not list(ROOT.glob('.project-import-*'))
# No archive extraction paths or SQL/table declarations are trusted.
stream=io.BytesIO()
with zipfile.ZipFile(stream,'w') as z:
 z.writestr('../outside','escape');z.writestr('manifest.json','{}')
try:import_project(token,archives._seal(stream.getvalue(),password),password,'BADPATH');raise AssertionError('Zip traversal accepted')
except ValueError:pass
# Reject a validly encrypted archive with hostile manifest references.
manifest,contents=archives._read_archive(blob,password)
manifest['documents'][0]['ref']='ORIG/../outside.md'
stream=io.BytesIO()
with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as z:
 for name,body in contents.items():z.writestr(name,json.dumps(manifest).encode() if name=='manifest.json' else body)
try:import_project(token,archives._seal(stream.getvalue(),password),password,'BADREF');raise AssertionError('Hostile document reference accepted')
except ValueError:pass
with patch.object(archives,'MAX_EXPANDED',16):
 try:import_project(token,blob,password,'BOMB');raise AssertionError('Expanded archive limit bypassed')
 except ValueError:pass
# A permission change during validation must be checked again before committing.
original_read=archives._read_archive
def revoke_during_read(*args):
 result=original_read(*args)
 execute('UPDATE users SET site_admin=0 WHERE id=?',(owner,))
 return result
with patch.object(archives,'_read_archive',side_effect=revoke_during_read):
 try:import_project(token,blob,password,'REVOKED');raise AssertionError('Demoted admin imported a project')
 except PermissionError:pass
assert not rows('SELECT * FROM projects WHERE id=?',('REVOKED',))
execute('UPDATE users SET site_admin=1 WHERE id=?',(owner,))
with patch.object(archives,'MAX_ARCHIVE',32):
 try:import_project(token,blob,password,'TOOBIG');raise AssertionError('Oversized archive accepted')
 except ValueError:pass
# Empty projects round-trip too.
import_project(token,export_project(token,'OTHER',password),password,'EMPTY')
assert rows('SELECT * FROM projects WHERE id=?',('EMPTY',))
print('PASS: encrypted project round-trip/history/authorship, super-admin restrictions, tampering, path/size checks, ID remapping, no privileges copied, atomic rollback')
