"""Project-scoped, password-encrypted transfers. No accounts or privileges are copied."""
import hashlib
import io
import json
import math
import os
import re
import shutil
import stat
import tempfile
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from auth import require_super_admin
from store import ROOT, STATUSES, db, digest, now, safe
from version import get_version

MAGIC=b'LINKABASE-PROJECT\x01'
MAX_ARCHIVE=64*1024*1024
MAX_EXPANDED=256*1024*1024
MAX_ENTRIES=10000
KEY_PATTERN=r'[A-Z][A-Z0-9]{1,9}'


def _password(password):
    if not isinstance(password,str) or not 12<=len(password)<=1024:
        raise ValueError('Use an archive password between 12 and 1024 characters.')
    return password.encode('utf-8')


def _key(password,salt):
    return Scrypt(salt=salt,length=32,n=2**16,r=8,p=1).derive(_password(password))


def _seal(raw,password):
    salt=os.urandom(16);nonce=os.urandom(12);header=MAGIC+salt+nonce
    return header+AESGCM(_key(password,salt)).encrypt(nonce,raw,header)


def _open(data,password):
    _password(password)
    size=len(MAGIC)+28
    if not isinstance(data,bytes) or len(data)>MAX_ARCHIVE or len(data)<size+16 or not data.startswith(MAGIC):
        raise ValueError('Not a supported Linkabase project archive (maximum 64 MiB).')
    header=data[:size];salt=header[len(MAGIC):len(MAGIC)+16];nonce=header[-12:]
    try:return AESGCM(_key(password,salt)).decrypt(nonce,data[size:],header)
    except InvalidTag:raise ValueError('Incorrect archive password or damaged archive.') from None


def _relative(value):
    if not isinstance(value,str) or not value or '\\' in value or '\x00' in value:
        raise ValueError('Invalid archive path.')
    path=PurePosixPath(value)
    if path.is_absolute() or any(p in ('..','.') for p in value.split('/')) or str(path)!=value:
        raise ValueError('Invalid archive path.')
    return path


def _document_ref(ref,project):
    path=_relative(ref)
    if len(path.parts)<2 or path.parts[0]!=project or path.suffix.lower()!='.md':
        raise ValueError('Document is outside the archived project.')
    return '/'.join(path.parts[1:])


def export_project(token,project,password):
    require_super_admin(token);_password(password)
    stream=io.BytesIO();expanded=0;count=0
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as archive,db() as connection:
        connection.execute('BEGIN IMMEDIATE');require_super_admin(token,connection)
        item=connection.execute('SELECT * FROM projects WHERE id=?',(project,)).fetchone()
        if not item:raise ValueError('Project not found.')
        def write(name,data):
            nonlocal expanded,count
            expanded+=len(data);count+=1
            if expanded>MAX_EXPANDED or count>MAX_ENTRIES:raise ValueError('Project exceeds the archive size or item limit.')
            archive.writestr(name,data)
            if stream.tell()>MAX_ARCHIVE:raise ValueError('Compressed project exceeds the 64 MiB limit.')
        manifest={'format':'linkabase-project','schema':1,'app_version':get_version(),'exported':now(),
                  'project':dict(item),'topics':[],'children':[],'tasks':[],'targets':[],'diagrams':[],'documents':[],'wiki_metadata':[]}
        for table,field in [('notes','topics'),('note_children','children'),('tasks','tasks')]:
            manifest[field]=[dict(row) for row in connection.execute('SELECT * FROM '+table+' WHERE project=?',(project,))]
        manifest['targets']=[dict(row) for row in connection.execute('SELECT x.* FROM task_targets x JOIN tasks t ON t.id=x.task WHERE t.project=?',(project,))]
        for index,row in enumerate(connection.execute('SELECT * FROM diagrams WHERE project=?',(project,))):
            diagram=dict(row);preview=diagram.pop('preview')
            diagram['preview_member']=f'previews/{index}.png' if preview else None
            if preview:write(diagram['preview_member'],preview)
            manifest['diagrams'].append(diagram)
        references={row['ref'] for row in manifest['children'] if row['kind']=='doc'}
        directory=safe(ROOT/'docs',project)
        if directory.exists():references.update(str(p.relative_to(ROOT/'docs')) for p in directory.rglob('*.md'))
        for index,ref in enumerate(sorted(references)):
            _document_ref(ref,project);path=safe(ROOT/'docs',ref)
            if not path.is_file():raise ValueError('A wiki document is missing; repair it before exporting.')
            body=path.read_bytes();body.decode('utf-8')
            member=f'documents/{index}.md';write(member,body)
            record={'ref':ref,'member':member,'modified':path.stat().st_mtime,'history':[]}
            history=safe(ROOT/'history',hashlib.sha256(ref.encode()).hexdigest())
            if history.exists():
                for revision in sorted(history.glob('*.md')):
                    revision=safe(history,revision.name)
                    revision_member=f'history/{index}/{revision.name}'
                    write(revision_member,revision.read_bytes())
                    record['history'].append({'member':revision_member,'name':revision.name,'modified':revision.stat().st_mtime})
            manifest['documents'].append(record)
            author=connection.execute('SELECT * FROM wiki_authorship WHERE path=?',(ref,)).fetchone()
            if author:
                metadata=dict(author)
                if metadata['content_digest']!=digest(body.decode('utf-8')):metadata['last_editor']='External edit'
                manifest['wiki_metadata'].append(metadata)
        write('manifest.json',json.dumps(manifest,ensure_ascii=False,allow_nan=False).encode())
    compressed=stream.getvalue()
    if len(compressed)+len(MAGIC)+44>MAX_ARCHIVE:raise ValueError('Compressed project exceeds the 64 MiB limit.')
    # Check our own output too, so an inconsistent source cannot produce an unusable backup.
    with zipfile.ZipFile(io.BytesIO(compressed)) as check:
        class Members:
            def __getitem__(self,name):return check.read(name)
            def __iter__(self):return iter(check.namelist())
        _validate(manifest,Members())
    result=_seal(compressed,password)
    if len(result)>MAX_ARCHIVE:raise ValueError('Encrypted project exceeds the 64 MiB limit.')
    return result


def _read_archive(data,password):
    raw=_open(data,password)
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries=archive.infolist()
            if len(entries)>MAX_ENTRIES or sum(i.file_size for i in entries)>MAX_EXPANDED:raise ValueError('Archive expands beyond the supported limit.')
            files={}
            for info in entries:
                _relative(info.filename)
                if info.filename in files or info.is_dir() or stat.S_ISLNK(info.external_attr>>16) or info.flag_bits&1 or info.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED):
                    raise ValueError('Unsupported or duplicate archive entry.')
                with archive.open(info) as source:body=source.read(info.file_size+1)
                if len(body)!=info.file_size:raise ValueError('Invalid archive size.')
                files[info.filename]=body
            manifest=json.loads(files['manifest.json'])
    except (zipfile.BadZipFile,KeyError,UnicodeError,RecursionError,RuntimeError) as error:
        raise ValueError('Invalid project archive.') from error
    _validate(manifest,files)
    return manifest,files


def _text(value,limit=4096):
    if not isinstance(value,str) or len(value)>limit:raise ValueError('Invalid archive text field.')
    return value


def _integer(value):
    if type(value) is not int or not 0<=value<2**63:raise ValueError('Invalid archive number.')
    return value


def _timestamp(value):
    if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=32503680000:raise ValueError('Invalid archive timestamp.')


def _validate(m,files):
    """Validate every reference before any database/file mutation; never execute SQL from an archive."""
    if not isinstance(m,dict) or m.get('format')!='linkabase-project' or type(m.get('schema')) is not int or m.get('schema')!=1:raise ValueError('Unsupported project archive format.')
    try:
        source=m['project'];project=_text(source['id'])
        if not re.fullmatch(KEY_PATTERN,project):raise ValueError('Invalid archived project key.')
        _text(source['name']);_text(source['description'],262144)
        groups={}
        for field in ['topics','children','tasks','diagrams','documents','targets','wiki_metadata']:
            if not isinstance(m[field],list) or len(m[field])>MAX_ENTRIES:raise ValueError('Invalid archive records.')
        for field in ['topics','children','tasks','diagrams']:
            ids=set()
            for row in m[field]:
                id=_text(row['id'])
                if not id or id in ids or row['project']!=project:raise ValueError('Invalid or cross-project record.')
                ids.add(id);_text(row['title'])
            groups[field]=ids
        for row in m['topics']:
            for key in ['summary','created','updated']:_text(row[key],262144)
        doc_refs=set();expected={'manifest.json'}
        for doc in m['documents']:
            _document_ref(doc['ref'],project)
            if doc['ref'] in doc_refs:raise ValueError('Duplicate wiki path.')
            doc_refs.add(doc['ref']);expected.add(doc['member']);files[doc['member']].decode('utf-8');_timestamp(doc['modified'])
            if not isinstance(doc['history'],list):raise ValueError('Invalid wiki history.')
            names=set()
            for revision in doc['history']:
                if not re.fullmatch(r'[A-Za-z0-9_-]+\.md',revision['name']) or revision['name'] in names:raise ValueError('Invalid revision filename.')
                names.add(revision['name']);expected.add(revision['member']);files[revision['member']].decode('utf-8');_timestamp(revision['modified'])
        for row in m['diagrams']:
            scene=json.loads(row['scene'])
            if not isinstance(scene,dict) or not isinstance(scene.get('elements'),list):raise ValueError('Invalid diagram scene.')
            if 'files' in scene and not isinstance(scene['files'],dict):raise ValueError('Invalid diagram images.')
            if 'appState' in scene and not isinstance(scene['appState'],dict):raise ValueError('Invalid diagram state.')
            _integer(row['version'])
            if row['preview_member']:
                expected.add(row['preview_member'])
                if not files[row['preview_member']].startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Invalid drawing preview.')
        for row in m['children']:
            if row['note'] not in groups['topics'] or row['kind'] not in ('doc','diagram'):raise ValueError('Invalid topic content.')
            if row['kind']=='doc' and row['ref'] not in doc_refs:raise ValueError('Wiki content is missing.')
            if row['kind']=='diagram' and row['ref'] not in groups['diagrams']:raise ValueError('Diagram content is missing.')
        linked=set()
        for row in m['targets']:
            if row['task'] not in groups['tasks'] or row['target_type']!='note' or row['target_id'] not in groups['topics'] or row['task'] in linked:raise ValueError('Invalid task-topic link.')
            linked.add(row['task'])
        for row in m['tasks']:
            if row['status'] not in STATUSES or row['priority'] not in ['High','Medium','Low']:raise ValueError('Invalid task status or priority.')
            for field in ['owner','due','doc','diagram']:_text(row[field])
            _text(row['description'],1024*1024)
            if row['doc'] and row['doc'] not in doc_refs:raise ValueError('Invalid legacy document reference.')
            if row['diagram'] and row['diagram'] not in groups['diagrams']:raise ValueError('Invalid legacy drawing reference.')
        seen=set()
        for row in m['wiki_metadata']:
            if row['path'] not in doc_refs or row['path'] in seen:raise ValueError('Invalid wiki attribution.')
            seen.add(row['path']);_text(row['author']);_text(row['last_editor']);_text(row['content_digest'])
        if expected!=set(files):raise ValueError('Archive contains missing or unexpected files.')
    except (KeyError,TypeError,AttributeError,UnicodeError,RecursionError) as error:
        raise ValueError('Invalid project manifest.') from error


def import_project(token,data,password,new_key,new_name=''):
    require_super_admin(token)
    new_key=new_key.strip();new_name=new_name.strip()
    if not re.fullmatch(KEY_PATTERN,new_key):raise ValueError('Use a new uppercase project key (2–10 letters/numbers).')
    m,files=_read_archive(data,password)
    name=new_name or m['project']['name'];_text(name)
    if not name:raise ValueError('Add a project name.')
    ids={field:{row['id']:(new_key+'-'+uuid.uuid4().hex[:16] if field=='tasks' else uuid.uuid4().hex) for row in m[field]} for field in ['topics','children','tasks','diagrams']}
    refs={doc['ref']:new_key+'/'+_document_ref(doc['ref'],m['project']['id']) for doc in m['documents']}
    destinations=[];moved=[]
    with tempfile.TemporaryDirectory(prefix='.project-import-',dir=ROOT) as temporary,db() as c:
        stage=Path(temporary)
        if m['documents']:
            docs=stage/'docs';docs.mkdir()
            for doc in m['documents']:
                target=safe(docs,_document_ref(doc['ref'],m['project']['id']));target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(files[doc['member']]);os.utime(target,(doc['modified'],doc['modified']))
                if doc['history']:
                    key=hashlib.sha256(refs[doc['ref']].encode()).hexdigest();history=stage/'history'/key;history.mkdir(parents=True)
                    for revision in doc['history']:
                        target=history/revision['name'];target.write_bytes(files[revision['member']]);os.utime(target,(revision['modified'],revision['modified']))
                    destinations.append((history,safe(ROOT/'history',key)))
            destinations.append((docs,safe(ROOT/'docs',new_key)))
        for drawing in m['diagrams']:
            target=stage/(ids['diagrams'][drawing['id']]+'.excalidraw');target.write_text(drawing['scene'])
            destinations.append((target,safe(ROOT/'diagrams',target.name)))
        try:
            c.execute('BEGIN IMMEDIATE');require_super_admin(token,c)
            if c.execute('SELECT 1 FROM projects WHERE id=?',(new_key,)).fetchone() or safe(ROOT/'docs',new_key).exists():raise ValueError('Project key or document directory already exists. Choose a new key.')
            if any(dst.exists() or dst.is_symlink() for _,dst in destinations):raise ValueError('Import destination already exists.')
            c.execute('INSERT INTO projects VALUES (?,?,?)',(new_key,name,m['project']['description']))
            for row in m['topics']:
                c.execute('INSERT INTO notes VALUES (?,?,?,?,?,?)',(ids['topics'][row['id']],new_key,row['title'],row['summary'],row['created'],row['updated']))
            for row in m['diagrams']:
                preview=files[row['preview_member']] if row['preview_member'] else None
                c.execute('INSERT INTO diagrams VALUES (?,?,?,?,?,?)',(ids['diagrams'][row['id']],new_key,row['title'],row['scene'],preview,row['version']))
            for row in m['children']:
                ref=refs[row['ref']] if row['kind']=='doc' else ids['diagrams'][row['ref']]
                c.execute('INSERT INTO note_children VALUES (?,?,?,?,?,?)',(ids['children'][row['id']],ids['topics'][row['note']],new_key,row['kind'],ref,row['title']))
            for row in m['tasks']:
                c.execute('INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?)',(ids['tasks'][row['id']],new_key,row['title'],row['status'],row['priority'],row['owner'],row['due'],row['description'],refs.get(row['doc'],''),ids['diagrams'].get(row['diagram'],'')))
            for row in m['targets']:
                c.execute('INSERT INTO task_targets VALUES (?,?,?)',(ids['tasks'][row['task']],'note',ids['topics'][row['target_id']]))
            metadata={row['path']:row for row in m['wiki_metadata']}
            for doc in m['documents']:
                ref=refs[doc['ref']];fingerprint=digest(files[doc['member']].decode('utf-8'))
                c.execute('INSERT INTO doc_versions VALUES (?,?)',(ref,fingerprint))
                author=metadata.get(doc['ref'],{})
                c.execute('INSERT INTO wiki_authorship VALUES (?,?,?,?)',(ref,author.get('author','Unknown'),author.get('last_editor','Unknown'),fingerprint))
            c.execute('INSERT INTO note_migrations VALUES (?)',(new_key,))
            for src,dst in destinations:
                src.replace(dst);moved.append(dst)
            c.commit()
        except BaseException:
            c.rollback()
            for path in reversed(moved):
                if path.is_dir():shutil.rmtree(path)
                else:path.unlink(missing_ok=True)
            raise
    return new_key
