import os, sqlite3, json, uuid, hashlib
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path(os.environ.get('WORKSPACE_DIR', './workspace')).resolve()
STATUSES = ['Backlog', 'Ready', 'In progress', 'Review', 'Done']
def now(): return datetime.now(timezone.utc).isoformat()
def db():
    ROOT.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(ROOT/'work.sqlite', timeout=20)
    c.row_factory = sqlite3.Row
    return c
def init():
    for p in ['docs','diagrams','history']: (ROOT/p).mkdir(parents=True,exist_ok=True)
    with db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT,description TEXT);
CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,project TEXT,title TEXT,status TEXT,priority TEXT,owner TEXT,due TEXT,description TEXT,doc TEXT,diagram TEXT);
CREATE TABLE IF NOT EXISTS diagrams(id TEXT PRIMARY KEY,project TEXT,title TEXT,scene TEXT,preview BLOB,version INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS doc_versions(path TEXT PRIMARY KEY,version TEXT);''')
def rows(sql,args=()):
    with db() as c: return [dict(x) for x in c.execute(sql,args)]
def execute(sql,args=()):
    with db() as c: c.execute(sql,args)
def safe(base, relative):
    base=Path(base).resolve(); p=(base/relative).resolve()
    if not p.is_relative_to(base) or p==base: raise ValueError('Invalid path')
    return p
def digest(text): return hashlib.sha256(text.encode()).hexdigest()
def save_doc(relative,text,expected):
    p=safe(ROOT/'docs',relative)
    # SQLite serializes saves and guards against stale browser edits.
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        old=p.read_text() if p.exists() else ''
        if digest(old)!=expected: raise ValueError('This note changed since you opened it. Reload before saving.')
        if p.exists():
            h=ROOT/'history'/hashlib.sha256(relative.encode()).hexdigest();h.mkdir(exist_ok=True)
            (h/(uuid.uuid4().hex+'.md')).write_text(old)
        p.parent.mkdir(parents=True,exist_ok=True)
        tmp=p.with_suffix('.tmp');tmp.write_text(text);tmp.replace(p)
        c.execute('INSERT OR REPLACE INTO doc_versions VALUES (?,?)',(relative,digest(text)))
def new_diagram(project,title):
    id=uuid.uuid4().hex
    execute('INSERT INTO diagrams(id,project,title,scene) VALUES (?,?,?,?)',(id,project,title,json.dumps({'type':'excalidraw','version':2,'source':'linkabase','elements':[],'appState':{'viewBackgroundColor':'#ffffff'},'files':{}})))
    return id
