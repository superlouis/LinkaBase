"""Focused regressions for drawing authorization, payload limits, and paths."""
import _bootstrap
import os,tempfile,asyncio,json,hashlib
from unittest.mock import patch
os.environ['WORKSPACE_DIR']=tempfile.mkdtemp()
import httpx
from fastapi import HTTPException
from store import init,new_diagram,rows,execute,safe,ROOT
from auth import init_auth,create_user,login,logout
from projects import create_project
init();init_auth()
owner=create_user('Owner','owner@example.com','password-12345',bootstrap=True)
token=login('owner@example.com','password-12345')
reader=create_user('Reader','reader@example.com','password-12345')
stranger=create_user('Other','other@example.com','password-12345')
read_token=login('reader@example.com','password-12345')
other_token=login('other@example.com','password-12345')
create_project(token,'Private','PRIVATE')
execute('INSERT INTO memberships VALUES (?,?,?)',(reader,'PRIVATE','read'))
drawing=new_diagram('PRIVATE','Private diagram')
import editor_api
headers={'Authorization':'Bearer '+token}
scene={'elements':[],'files':{},'appState':{}}
payload={'scene':scene,'version':0}

async def check():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=editor_api.app),base_url='http://testserver') as client:
        for id in [drawing,'missing']:
            response=await client.get('/api/drawings/'+id)
            assert response.status_code==401
            assert response.headers['www-authenticate']=='Bearer'
            assert response.headers['cache-control']=='no-store'
        response=await client.get('/api/drawings/'+drawing,headers={'Authorization':'Bearer '+other_token})
        assert response.status_code==404
        response=await client.get('/api/drawings/'+drawing,headers={'Authorization':'Bearer '+read_token})
        assert response.status_code==200 and not response.json()['writable']
        assert response.headers['cache-control']=='no-store'
        assert response.headers['referrer-policy']=='no-referrer'
        response=await client.put('/api/drawings/'+drawing,headers={'Authorization':'Bearer '+read_token},json=payload)
        assert response.status_code==403
        for invalid in [[],{}, {'scene':None,'version':0}, {'scene':[],'version':0},
                        {'scene':scene,'version':True},{'scene':scene,'version':2**70},
                        {'scene':scene,'version':-1},{'scene':dict(scene,files=[]),'version':0},
                        {'scene':scene,'version':0,'preview':'not base64'}]:
            response=await client.put('/api/drawings/'+drawing,headers=headers,json=invalid)
            assert response.status_code==400,(invalid,response.status_code)
        assert rows('SELECT version FROM diagrams WHERE id=?',(drawing,))[0]['version']==0
        with patch.object(editor_api,'MAX_DRAWING_BYTES',32):
            response=await client.put('/api/drawings/'+drawing,headers=headers,content=b'x'*33)
            assert response.status_code==413
        response=await client.put('/api/drawings/'+drawing,headers=headers,json=payload)
        assert response.status_code==200 and response.json()=={'version':1}
        response=await client.put('/api/drawings/'+drawing,headers=headers,json=payload)
        assert response.status_code==409
        # Validating access on every request makes account revocation immediate.
        logout(read_token)
        assert (await client.get('/api/drawings/'+drawing,headers={'Authorization':'Bearer '+read_token})).status_code==401
        execute('UPDATE sessions SET expires=0 WHERE token=?',(hashlib.sha256(token.encode()).hexdigest(),))
        assert (await client.get('/api/drawings/'+drawing,headers=headers)).status_code==401
    class Chunked:
        headers={}
        async def stream(self):
            yield b'x'*24
            yield b'x'*24
            raise AssertionError('Reader continued after exceeding the limit')
    with patch.object(editor_api,'MAX_DRAWING_BYTES',32):
        try:
            await editor_api.drawing_body(Chunked())
            raise AssertionError('Chunked limit bypassed')
        except HTTPException as error:assert error.status_code==413

asyncio.run(asyncio.wait_for(check(),timeout=25))
for path in ['../outside','/etc/passwd']:
    try:safe(ROOT,path);raise AssertionError('Traversal accepted')
    except ValueError:pass
with tempfile.TemporaryDirectory() as outside:
    (ROOT/'escape').symlink_to(outside,target_is_directory=True)
    try:safe(ROOT,'escape/secret');raise AssertionError('Symlink escape accepted')
    except ValueError:pass
print('PASS: API authorization, revocation, cache headers, malformed payloads, bounded streaming, stale writes, path confinement')
