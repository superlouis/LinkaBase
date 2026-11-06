"""Local accounts and project authorization shared by Streamlit and drawing API."""
import hashlib,hmac,secrets,time
from store import db,rows
LEVEL={'read':1,'write':2,'admin':3}
def init_auth():
    with db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT,site_admin INTEGER DEFAULT 0,active INTEGER DEFAULT 1,theme TEXT DEFAULT 'Paper');
CREATE TABLE IF NOT EXISTS memberships(user TEXT,project TEXT,role TEXT,PRIMARY KEY(user,project));
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user TEXT,expires REAL);
CREATE TABLE IF NOT EXISTS login_attempts(email TEXT PRIMARY KEY,failures INTEGER,blocked_until REAL);''')
def password_hash(password):
    if len(password)<12: raise ValueError('Use at least 12 characters.')
    salt=secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),600000).hex()
def create_user(name,email,password,bootstrap=False):
    name=name.strip();email=email.strip().lower()
    if not name or '@' not in email: raise ValueError('Enter a name and valid email.')
    hashed=password_hash(password);id=secrets.token_hex(16)
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        if bootstrap and c.execute('SELECT 1 FROM users').fetchone(): raise ValueError('Setup already completed. Sign in.')
        c.execute('INSERT INTO users(id,name,email,password,site_admin,theme) VALUES (?,?,?,?,?,?)',(id,name,email,hashed,int(bootstrap),'Paper'))
    return id
def login(email,password):
    email=email.strip().lower();t=time.time()
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        a=c.execute('SELECT * FROM login_attempts WHERE email=?',(email,)).fetchone()
        if a and a['blocked_until']>t: raise ValueError('Too many attempts. Try again in 5 minutes.')
        u=c.execute('SELECT * FROM users WHERE email=? AND active=1',(email,)).fetchone()
        salt,stored=u['password'].split(':') if u else ('dummy-salt','0'*64)
        valid=hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),600000).hex(),stored)
        if not u or not valid:
            n=(a['failures'] if a else 0)+1
            c.execute('INSERT OR REPLACE INTO login_attempts VALUES (?,?,?)',(email,n,t+300 if n>=5 else 0))
            error=True
        else:
            c.execute('DELETE FROM login_attempts WHERE email=?',(email,));token=secrets.token_urlsafe(40)
            c.execute('INSERT INTO sessions VALUES (?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),u['id'],t+43200));error=False
    if error: raise ValueError('Incorrect email or password.')
    return token
def user_for(token):
    if not token:return None
    r=rows('SELECT u.* FROM users u JOIN sessions s ON u.id=s.user WHERE s.token=? AND s.expires>? AND u.active=1',(hashlib.sha256(token.encode()).hexdigest(),time.time()))
    return r[0] if r else None
def role_for(user,project):
    if not user:return None
    fresh=rows('SELECT active,site_admin FROM users WHERE id=?',(user['id'],))
    if not fresh or not fresh[0]['active']:return None
    if fresh[0]['site_admin']:return 'admin'
    r=rows('SELECT role FROM memberships WHERE user=? AND project=?',(user['id'],project))
    return r[0]['role'] if r else None
def require(token,project,level='read'):
    u=user_for(token)
    if LEVEL.get(role_for(u,project),0)<LEVEL[level]: raise PermissionError('Your project access does not allow this action.')
    return u
def logout(token):
    with db() as c:c.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(token.encode()).hexdigest(),))


def set_super_admin(token, target, enabled):
    """Only a live super-admin may change workspace privileges; keep one active."""
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        actor=c.execute('SELECT u.* FROM users u JOIN sessions s ON s.user=u.id WHERE s.token=? AND s.expires>? AND u.active=1', (hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
        if not actor or not actor['site_admin']:raise PermissionError('Super-admin access required.')
        selected=c.execute('SELECT * FROM users WHERE id=?',(target,)).fetchone()
        if not selected or not selected['active']:raise ValueError('Choose an active account.')
        if not enabled and selected['site_admin'] and c.execute('SELECT COUNT(*) FROM users WHERE site_admin=1 AND active=1').fetchone()[0]<=1:raise ValueError('Keep at least one active super-admin.')
        c.execute('UPDATE users SET site_admin=? WHERE id=?',(int(enabled),target))
