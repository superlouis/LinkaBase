"""Additive note/child/task-target model. Does not move existing files."""
import uuid
from datetime import datetime
from store import db,rows,ROOT,now
from auth import require
KINDS={'doc':'Wiki page','diagram':'Drawing'}
def init_notes():
    with db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS notes(id TEXT PRIMARY KEY,project TEXT NOT NULL,title TEXT NOT NULL,summary TEXT DEFAULT '',created TEXT,updated TEXT);
CREATE TABLE IF NOT EXISTS note_children(id TEXT PRIMARY KEY,note TEXT NOT NULL,project TEXT NOT NULL,kind TEXT NOT NULL,ref TEXT NOT NULL,title TEXT NOT NULL,UNIQUE(project,kind,ref));
CREATE TABLE IF NOT EXISTS task_targets(task TEXT PRIMARY KEY,target_type TEXT NOT NULL,target_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS note_migrations(project TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS task_assignees(task TEXT PRIMARY KEY,user TEXT NOT NULL);''')
        # Preserve old content links as links to the content's current parent topic.
        c.execute("""UPDATE task_targets SET target_type='note',target_id=(
            SELECT n.id FROM note_children child JOIN notes n ON n.id=child.note
            JOIN tasks t ON t.id=task_targets.task
            WHERE child.id=task_targets.target_id AND child.project=t.project AND n.project=t.project
        ) WHERE target_type='child' AND EXISTS(
            SELECT 1 FROM note_children child JOIN notes n ON n.id=child.note
            JOIN tasks t ON t.id=task_targets.task
            WHERE child.id=task_targets.target_id AND child.project=t.project AND n.project=t.project
        )""")
        # Missing or invalid legacy content cannot supply a valid topic.
        c.execute("DELETE FROM task_targets WHERE target_type='child'")
        from migrations import retire_storage
        retire_storage(c)
def sync_project(project):
    """Import ungrouped content and legacy task links; safe to call repeatedly."""
    found=[]
    directory=ROOT/'docs'/project
    if directory.exists():
        for f in directory.rglob('*.md'):
            if f.resolve().is_relative_to((ROOT/'docs').resolve()):found.append(('doc',str(f.relative_to(ROOT/'docs')),f.stem))
    found += [('diagram',x['id'],x['title']) for x in rows('SELECT id,title FROM diagrams WHERE project=?',(project,))]
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        default='library:'+project
        missing=[item for item in found if not c.execute('SELECT 1 FROM note_children WHERE project=? AND kind=? AND ref=?',(project,item[0],item[1])).fetchone()]
        if missing:
            c.execute('INSERT OR IGNORE INTO notes VALUES (?,?,?,?,?,?)',(default,project,'Project library','Existing content and newly discovered vault pages.',now(),now()))
        for kind,ref,title in missing:
            c.execute('INSERT OR IGNORE INTO note_children VALUES (?,?,?,?,?,?)',(uuid.uuid4().hex,default,project,kind,ref,title))
        if not c.execute('SELECT 1 FROM note_migrations WHERE project=?',(project,)).fetchone():
            for t in c.execute('SELECT id,doc,diagram FROM tasks WHERE project=?',(project,)).fetchall():
                child=None
                for kind,ref in [('doc',t['doc']),('diagram',t['diagram'])]:
                    if ref:
                        child=c.execute('SELECT id,note FROM note_children WHERE project=? AND kind=? AND ref=?',(project,kind,ref)).fetchone()
                        if child:break
                if child:c.execute('INSERT OR IGNORE INTO task_targets VALUES (?,?,?)',(t['id'],'note',child['note']))
            c.execute('INSERT INTO note_migrations VALUES (?)',(project,))
def list_notes(token,project):
    require(token,project)
    return rows('SELECT n.*,COUNT(c.id) AS child_count FROM notes n LEFT JOIN note_children c ON n.id=c.note WHERE n.project=? GROUP BY n.id ORDER BY n.updated DESC,n.title',(project,))
def children(token,project,note=None,kind=None):
    if kind is not None and kind not in KINDS:raise ValueError('Invalid content type.')
    require(token,project);sql='SELECT c.*,n.title AS note_title FROM note_children c JOIN notes n ON n.id=c.note WHERE c.project=?';args=[project]
    if note:sql+=' AND c.note=?';args.append(note)
    if kind:sql+=' AND c.kind=?';args.append(kind)
    return rows(sql+' ORDER BY c.kind,c.title',args)
def create_note(token,project,title,summary=''):
    require(token,project,'write')
    if not title.strip():raise ValueError('Add a topic title.')
    id=uuid.uuid4().hex
    with db() as c:c.execute('INSERT INTO notes VALUES (?,?,?,?,?,?)',(id,project,title.strip(),summary,now(),now()))
    return id
def edit_note(token,project,id,title,summary):
    require(token,project,'write')
    if not title.strip():raise ValueError('Add a topic title.')
    with db() as c:
        if not c.execute('UPDATE notes SET title=?,summary=?,updated=? WHERE id=? AND project=?',(title.strip(),summary,now(),id,project)).rowcount:raise ValueError('Topic not found.')
def add_child(token,project,note,kind,ref,title):
    require(token,project,'write')
    if kind not in KINDS:raise ValueError('Invalid child type.')
    with db() as c:
        if not c.execute('SELECT 1 FROM notes WHERE id=? AND project=?',(note,project)).fetchone():raise ValueError('Topic is outside this project.')
        if kind=='doc':
            from store import safe
            path=safe(ROOT/'docs'/project,str(ref).removeprefix(project+'/'))
            if not str(ref).startswith(project+'/') or not path.exists():raise ValueError('Document is outside this project.')
        elif not c.execute('SELECT 1 FROM diagrams WHERE id=? AND project=?',(ref,project)).fetchone():raise ValueError('Content is outside this project.')
        existing=c.execute('SELECT id FROM note_children WHERE project=? AND kind=? AND ref=?',(project,kind,ref)).fetchone()
        id=existing['id'] if existing else uuid.uuid4().hex
        c.execute('INSERT OR REPLACE INTO note_children VALUES (?,?,?,?,?,?)',(id,note,project,kind,ref,title))
        c.execute('UPDATE notes SET updated=? WHERE id=?',(now(),note))
    return id
def move_child(token,project,child,note):
    require(token,project,'write')
    with db() as c:
        if not c.execute('SELECT 1 FROM notes WHERE id=? AND project=?',(note,project)).fetchone():raise ValueError('Topic not found.')
        if not c.execute('UPDATE note_children SET note=? WHERE id=? AND project=?',(note,child,project)).rowcount:raise ValueError('Child not found.')
        c.execute('UPDATE notes SET updated=? WHERE id=?',(now(),note))
def target_choices(token,project):
    opts={'':'No linked topic'}
    for n in list_notes(token,project):
        opts['note:'+n['id']]='Topic · '+n['title']
    return opts
def save_task(token,project,id,fields,target='',assignee=...):
    require(token,project,'write')
    if not fields['title'].strip():raise ValueError('Add a task title.')
    from store import STATUSES
    if fields['status'] not in STATUSES or fields['priority'] not in ['High','Medium','Low']:raise ValueError('Invalid status or priority.')
    if fields['due']:datetime.strptime(fields['due'],'%Y-%m-%d')
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        parts=target.split(':',1) if target else None
        if parts:
            if len(parts)!=2 or parts[0]!='note' or not parts[1]:raise ValueError('Tasks can only be linked to a topic.')
            kind,ref=parts
            if not c.execute('SELECT 1 FROM notes WHERE id=? AND project=?',(ref,project)).fetchone():raise ValueError('Topic is outside this project.')
        existing=c.execute('SELECT project FROM tasks WHERE id=?',(id,)).fetchone()
        if existing and existing['project']!=project:raise ValueError('Task is outside this project.')
        fields=dict(fields)
        if assignee is not ...:
            if assignee=='__legacy__':
                old=c.execute('SELECT owner FROM tasks WHERE id=? AND project=?',(id,project)).fetchone()
                if not old or not old['owner']:raise ValueError('No previous assignment exists.')
                fields['owner']=old['owner']
            elif assignee:
                person=c.execute('SELECT u.id,u.name FROM users u WHERE u.id=? AND u.active=1 AND (u.site_admin=1 OR EXISTS(SELECT 1 FROM memberships m WHERE m.user=u.id AND m.project=?))',(assignee,project)).fetchone()
                if not person:raise ValueError('Choose an active user with access to this project.')
                fields['owner']=person['name']
            else:fields['owner']=''
            c.execute('DELETE FROM task_assignees WHERE task=?',(id,))
            if assignee and assignee!='__legacy__':c.execute('INSERT INTO task_assignees VALUES (?,?)',(id,assignee))
        values=tuple(fields[k] for k in ['title','status','priority','owner','due','description'])
        if existing:c.execute('UPDATE tasks SET title=?,status=?,priority=?,owner=?,due=?,description=? WHERE id=? AND project=?',(*values,id,project))
        else:c.execute('INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?)',(id,project,*values,'',''))
        c.execute('DELETE FROM task_targets WHERE task=?',(id,))
        if parts:c.execute('INSERT INTO task_targets VALUES (?,?,?)',(id,*parts))
def task_targets(project):
    return {x['task']:'note:'+x['target_id'] for x in rows("SELECT tt.* FROM task_targets tt JOIN tasks t ON t.id=tt.task JOIN notes n ON n.id=tt.target_id AND n.project=t.project WHERE t.project=? AND tt.target_type='note'",(project,))}

def delete_content(token,project,id,whole_base=False):
    """Remove active content, archive local files and records, retain tasks."""
    import json,base64,shutil
    from pathlib import Path
    from store import safe
    require(token,project,'write')
    archive_id=uuid.uuid4().hex;archive=ROOT/'trash'/archive_id
    moved=[]
    def encode(value):
        if isinstance(value,bytes):return {'base64':base64.b64encode(value).decode()}
        raise TypeError(type(value).__name__)
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        c.execute('CREATE TABLE IF NOT EXISTS trash_entries(id TEXT PRIMARY KEY,project TEXT,kind TEXT,title TEXT,payload TEXT,deleted TEXT)')
        if whole_base:
            base=c.execute('SELECT * FROM notes WHERE id=? AND project=?',(id,project)).fetchone()
            if not base:raise ValueError('Topic not found.')
            items=c.execute('SELECT * FROM note_children WHERE note=? AND project=?',(id,project)).fetchall();title=base['title']
        else:
            item=c.execute('SELECT * FROM note_children WHERE id=? AND project=?',(id,project)).fetchone()
            if not item:raise ValueError('Content not found.')
            items=[item];base=None;title=item['title']
        payload={'base':dict(base) if base else None,'children':[],'task_links':[],'files':[]}
        paths=[]
        for row in items:
            child=dict(row);kind=child['kind'];ref=child['ref'];source=None
            if kind=='doc':
                path=safe(ROOT/'docs',ref)
                if not path.is_relative_to((ROOT/'docs'/project).resolve()):raise ValueError('Document is outside this project.')
                if path.exists():paths.append(path)
                history=ROOT/'history'/__import__('hashlib').sha256(ref.encode()).hexdigest()
                if history.exists():paths.append(history)
                c.execute('UPDATE tasks SET doc=? WHERE project=? AND doc=?',('',project,ref))
                metadata=c.execute('SELECT * FROM wiki_authorship WHERE path=?',(ref,)).fetchone()
                if metadata:child['authorship']=dict(metadata)
                c.execute('DELETE FROM wiki_authorship WHERE path=?',(ref,))
            elif kind=='diagram':
                source=c.execute('SELECT * FROM diagrams WHERE id=? AND project=?',(ref,project)).fetchone()
                path=safe(ROOT/'diagrams',ref+'.excalidraw')
                if path.exists():paths.append(path)
                c.execute('DELETE FROM diagrams WHERE id=? AND project=?',(ref,project))
                c.execute('UPDATE tasks SET diagram=? WHERE project=? AND diagram=?',('',project,ref))
            else:raise ValueError('Unsupported content type.')
            payload['children'].append({'child':child,'source':dict(source) if source else None})
            links=c.execute("SELECT tt.* FROM task_targets tt JOIN tasks t ON t.id=tt.task WHERE t.project=? AND tt.target_type='child' AND tt.target_id=?",(project,child['id'])).fetchall()
            payload['task_links'] += [dict(x) for x in links]
            c.execute("DELETE FROM task_targets WHERE target_type='child' AND target_id=? AND task IN (SELECT id FROM tasks WHERE project=?)",(child['id'],project))
            c.execute('DELETE FROM note_children WHERE id=? AND project=?',(child['id'],project))
        if whole_base:
            links=c.execute("SELECT tt.* FROM task_targets tt JOIN tasks t ON t.id=tt.task WHERE t.project=? AND tt.target_type='note' AND tt.target_id=?",(project,id)).fetchall()
            payload['task_links'] += [dict(x) for x in links]
            c.execute("DELETE FROM task_targets WHERE target_type='note' AND target_id=? AND task IN (SELECT id FROM tasks WHERE project=?)",(id,project))
            c.execute('DELETE FROM notes WHERE id=? AND project=?',(id,project))
        try:
            for src in dict.fromkeys(paths):
                dest=archive/src.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);src.replace(dest);moved.append((src,dest));payload['files'].append(str(src.relative_to(ROOT)))
            encoded=json.dumps(payload,default=encode)
            archive.mkdir(parents=True,exist_ok=True);(archive/'manifest.json').write_text(encoded)
            c.execute('INSERT INTO trash_entries VALUES (?,?,?,?,?,?)',(archive_id,project,'base' if whole_base else 'child',title,encoded,now()))
            c.commit()
        except BaseException:
            c.rollback()
            for src,dest in reversed(moved):src.parent.mkdir(parents=True,exist_ok=True);dest.replace(src)
            shutil.rmtree(archive,ignore_errors=True)
            raise
    return archive_id


def project_users(token,project):
    """Only active users with access to this project; never returns credentials."""
    require(token,project)
    return rows('SELECT u.id,u.name,u.email FROM users u WHERE u.active=1 AND (u.site_admin=1 OR EXISTS(SELECT 1 FROM memberships m WHERE m.user=u.id AND m.project=?)) ORDER BY lower(u.name),u.email',(project,))
