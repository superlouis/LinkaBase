"""Project management with project-scoped admin checks and recoverable deletion."""
import json,base64,re,uuid,shutil
from pathlib import Path
from store import ROOT,db,rows,safe,now
from auth import require,user_for

def create_project(token,name,key,description=''):
    user=user_for(token)
    if not user or not user['site_admin']:raise PermissionError('Only super-admins can create projects.')
    name=name.strip();key=key.strip()
    if not name or not re.fullmatch('[A-Z][A-Z0-9]{1,9}',key):raise ValueError('Use a project name and an uppercase key (2–10 letters/numbers).')
    with db() as c:
        if c.execute('SELECT 1 FROM projects WHERE id=?',(key,)).fetchone():raise ValueError('Project key already exists.')
        c.execute('INSERT INTO projects VALUES (?,?,?)',(key,name,description))
    return key

def rename_project(token,project,name):
    require(token,project,'admin')
    if not name.strip():raise ValueError('Enter a project name.')
    with db() as c:
        if not c.execute('UPDATE projects SET name=? WHERE id=?',(name.strip(),project)).rowcount:raise ValueError('Project not found.')

def project_counts(token,project):
    require(token,project,'admin')
    return {label:rows('SELECT COUNT(*) AS n FROM '+table+' WHERE project=?',(project,))[0]['n'] for label,table in [('tasks','tasks'),('topics','notes'),('drawings','diagrams')]}

def delete_project(token,project):
    """Remove a live project atomically, retaining an archive and all user accounts."""
    require(token,project,'admin')
    archive_id=uuid.uuid4().hex;archive=ROOT/'trash'/archive_id;moved=[]
    def encode(value):
        if isinstance(value,bytes):return {'base64':base64.b64encode(value).decode()}
        raise TypeError(type(value).__name__)
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM projects WHERE id=?',(project,)).fetchone()
        if not row:raise ValueError('Project not found.')
        snapshot={'project':dict(row),'tables':{},'files':[]};paths=[]
        for table in ['tasks','notes','note_children','diagrams','memberships','note_migrations']:
            snapshot['tables'][table]=[dict(x) for x in c.execute('SELECT * FROM '+table+' WHERE project=?',(project,))]
        for table in ['task_targets','task_assignees']:
            snapshot['tables'][table]=[dict(x) for x in c.execute('SELECT x.* FROM '+table+' x JOIN tasks t ON t.id=x.task WHERE t.project=?',(project,))]
        prefix=project+'/'
        snapshot['tables']['doc_versions']=[dict(x) for x in c.execute('SELECT * FROM doc_versions WHERE substr(path,1,?)=?',(len(prefix),prefix))]
        snapshot['tables']['wiki_authorship']=[dict(x) for x in c.execute('SELECT * FROM wiki_authorship WHERE substr(path,1,?)=?',(len(prefix),prefix))]
        docdir=safe(ROOT/'docs',project)
        docrefs={x['path'] for x in snapshot['tables']['doc_versions']}
        docrefs.update(x['ref'] for x in snapshot['tables']['note_children'] if x['kind']=='doc' and x['ref'].startswith(prefix))
        if docdir.exists():
            docrefs.update(str(x.relative_to(ROOT/'docs')) for x in docdir.rglob('*.md'))
            paths.append(docdir)
        import hashlib
        for ref in docrefs:
            h=ROOT/'history'/hashlib.sha256(ref.encode()).hexdigest()
            if h.exists():paths.append(h)
        for d in snapshot['tables']['diagrams']:
            path=safe(ROOT/'diagrams',d['id']+'.excalidraw')
            if path.exists():paths.append(path)
        c.execute('CREATE TABLE IF NOT EXISTS trash_entries(id TEXT PRIMARY KEY,project TEXT,kind TEXT,title TEXT,payload TEXT,deleted TEXT)')
        for table in ['task_targets','task_assignees']:c.execute('DELETE FROM '+table+' WHERE task IN (SELECT id FROM tasks WHERE project=?)',(project,))
        for table in ['memberships','note_children','notes','tasks','diagrams','note_migrations']:c.execute('DELETE FROM '+table+' WHERE project=?',(project,))
        c.execute('DELETE FROM doc_versions WHERE substr(path,1,?)=?',(len(prefix),prefix))
        c.execute('DELETE FROM wiki_authorship WHERE substr(path,1,?)=?',(len(prefix),prefix))
        c.execute('DELETE FROM projects WHERE id=?',(project,))
        try:
            for src in dict.fromkeys(paths):
                dest=archive/src.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);src.replace(dest);moved.append((src,dest));snapshot['files'].append(str(src.relative_to(ROOT)))
            archive.mkdir(parents=True,exist_ok=True);payload=json.dumps(snapshot,default=encode);(archive/'manifest.json').write_text(payload)
            c.execute('INSERT INTO trash_entries VALUES (?,?,?,?,?,?)',(archive_id,project,'project',row['name'],payload,now()));c.commit()
        except BaseException:
            c.rollback()
            for src,dest in reversed(moved):src.parent.mkdir(parents=True,exist_ok=True);dest.replace(src)
            shutil.rmtree(archive,ignore_errors=True)
            raise
    return archive_id
