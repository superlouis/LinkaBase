"""Wiki author/last-editor attribution, external edits, and safe HTML output."""
import _bootstrap
import os,tempfile
os.environ['WORKSPACE_DIR']=tempfile.mkdtemp()
from store import init,save_doc,digest,rows,ROOT
from auth import init_auth,create_user,login
from notes import init_notes,create_note,add_child,children,delete_content
from projects import create_project
from library_surface import library_markup
init();init_auth();init_notes()
create_user('Alice','alice@example.com','password-12345',bootstrap=True)
token=login('alice@example.com','password-12345');create_project(token,'Wiki','WIKI');topic=create_note(token,'WIKI','Guides')
save_doc('WIKI/Guide.md','# First',digest(''),actor='Alice')
child=add_child(token,'WIKI',topic,'doc','WIKI/Guide.md','Guide')
save_doc('WIKI/Guide.md','# Second',digest('# First'),actor='Bob <editor>')
metadata=rows('SELECT * FROM wiki_authorship WHERE path=?',('WIKI/Guide.md',))[0]
assert metadata['author']=='Alice' and metadata['last_editor']=='Bob <editor>'
markup=library_markup(children(token,'WIKI'),'doc',{topic:'Guides'},'WIKI')
assert '>Author<' in markup and '>Last editor<' in markup
assert 'Bob &lt;editor&gt;' in markup and 'Bob <editor>' not in markup
try:save_doc('WIKI/Guide.md','Bad',digest('outdated'),actor='Wrong');raise AssertionError('Conflict accepted')
except ValueError:pass
assert rows('SELECT last_editor FROM wiki_authorship WHERE path=?',('WIKI/Guide.md',))[0]['last_editor']=='Bob <editor>'
(ROOT/'docs/WIKI/Guide.md').write_text('# External change')
assert 'External edit' in library_markup(children(token,'WIKI'),'doc',{topic:'Guides'},'WIKI')
# Existing documents cannot be assigned a fabricated historical author.
(ROOT/'docs/WIKI/Legacy.md').write_text('# Old page')
save_doc('WIKI/Legacy.md','# Changed',digest('# Old page'),actor='Alice')
legacy=rows('SELECT * FROM wiki_authorship WHERE path=?',('WIKI/Legacy.md',))[0]
assert legacy['author']=='Unknown' and legacy['last_editor']=='Alice'
archive=delete_content(token,'WIKI',child)
assert not rows('SELECT * FROM wiki_authorship WHERE path=?',('WIKI/Guide.md',))
import json
payload=json.loads((ROOT/'trash'/archive/'manifest.json').read_text())
assert payload['children'][0]['child']['authorship']['author']=='Alice'
print('PASS: author/editor tracking, legacy unknowns, conflict protection, external edits, escaped table cells, archived attribution')
