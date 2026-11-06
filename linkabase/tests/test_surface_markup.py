"""Custom surfaces escape user content and preserve IDs for event routing."""
import _bootstrap
import os,tempfile
os.environ['WORKSPACE_DIR']=tempfile.mkdtemp()
from html.parser import HTMLParser
from store import init,save_doc,digest
from auth import init_auth
from notes import init_notes
from collections_ui import topic_markup
from library_surface import library_markup
from surface import action

init();init_auth();init_notes()
unsafe='\"><img src=x onerror=alert(1)>'
note={'id':'topic&"id','title':unsafe,'child_count':1}
child={'id':'child&"id','title':unsafe,'note':note['id'],'kind':'doc','ref':'PROJECT/page.md'}
save_doc(child['ref'],'# A document',digest(''))
class Inspect(HTMLParser):
 def __init__(self):super().__init__();self.buttons=[];self.tags=[]
 def handle_starttag(self,tag,attrs):
  self.tags.append(tag)
  if tag=='button':self.buttons.append(dict(attrs))
for markup in [topic_markup([note],[child]), library_markup([child],'doc',{note['id']:unsafe},'PROJECT'),action(unsafe,'topic',note['id'])]:
 parser=Inspect();parser.feed(markup)
 assert 'script' not in parser.tags and 'img' not in parser.tags
 assert unsafe not in markup and '&lt;img' in markup
 assert any(b.get('data-id') in {note['id'],child['id']} for b in parser.buttons)
 assert all(b.get('aria-label') for b in parser.buttons)
assert '1 page' in topic_markup([note],[child]) and '1 pages' not in topic_markup([note],[child])
print('PASS: custom surface HTML escaping, accessible labels, and event identifiers')
