import os,tempfile
os.environ['WORKSPACE_DIR']=tempfile.mkdtemp()
from store import init,execute,rows
from auth import *
from projects import create_project,rename_project
init();init_auth()
a=create_user('Super','super@example.com','password-12345',bootstrap=True);at=login('super@example.com','password-12345')
b=create_user('Admin','admin@example.com','password-12345');bt=login('admin@example.com','password-12345')
create_project(at,'One','ONE');create_project(at,'Two','TWO');execute('INSERT INTO memberships VALUES (?,?,?)',(b,'ONE','admin'))
rename_project(bt,'ONE','Renamed')
for f in [lambda:create_project(bt,'Denied','NOPE'),lambda:rename_project(bt,'TWO','Denied'),lambda:set_super_admin(bt,b,True),lambda:set_super_admin(at,a,False)]:
 try:f();raise AssertionError('Unauthorized or last-admin mutation succeeded')
 except (PermissionError,ValueError):pass
set_super_admin(at,b,True);assert user_for(bt)['site_admin'];create_project(bt,'Three','THREE')
set_super_admin(bt,a,False);assert not user_for(at)['site_admin'];assert role_for(user_for(bt),'TWO')=='admin'
print('PASS: project scope, super-admin creation/promotion/demotion, last-active guard')
