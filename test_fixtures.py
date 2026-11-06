"""Explicit sample content for tests only; never called by the application."""
from store import db,ROOT

def seed_projects():
    with db() as c:
        c.execute('INSERT OR IGNORE INTO projects VALUES (?,?,?)',('PLAT','Test Platform','Test project'))
        c.execute('INSERT OR IGNORE INTO projects VALUES (?,?,?)',('RES','Test Research','Test project'))
        for i,(title,status,priority) in enumerate([('Define a protocol','In progress','High'),('Document evaluation','Ready','Medium'),('Map architecture','Review','Medium'),('Review permissions','Backlog','High'),('Create a handbook','Done','Low')],1):
            c.execute('INSERT OR IGNORE INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?)',(f'PLAT-{i:03}','PLAT',title,status,priority,'Steph-Yves','','Test fixture','PLAT/Welcome.md',''))
    directory=ROOT/'docs/PLAT';directory.mkdir(parents=True,exist_ok=True)
    (directory/'Welcome.md').write_text('# Test handbook\n')
