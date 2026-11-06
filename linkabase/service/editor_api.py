import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import json, base64, re, os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from store import init,db,rows,ROOT
from auth import init_auth,require,role_for,user_for
app=FastAPI(title='Linkabase drawing service',docs_url=None,redoc_url=None,openapi_url=None)
MAX_DRAWING_BYTES=25*1024*1024

@app.middleware('http')
async def private_responses(request,call_next):
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    if request.url.path.startswith(('/api/','/editor/')):
        response.headers['Cache-Control']='no-store'
    return response
init();init_auth()
DIST=Path(os.environ.get('EDITOR_DIST_DIR',str(Path(__file__).resolve().parents[1]/'editor_dist'))).resolve()
if DIST.exists(): app.mount('/studio-assets', StaticFiles(directory=DIST), name='studio-assets')
@app.get('/health')
def health(): return {'ok':True}
@app.get('/editor/{id}',response_class=HTMLResponse)
def editor(id:str):
    # The shell has no drawing data. Do not reveal whether an ID exists before authentication.
    if not (DIST/'index.html').exists(): raise HTTPException(503,'Editor assets missing. Build the frontend or rebuild the Docker image.')
    return HTMLResponse((DIST/'index.html').read_text(),headers={'Referrer-Policy':'no-referrer','Cache-Control':'no-store'})
def authorize(request,id,level='read'):
    scheme,_,token=request.headers.get('authorization','').partition(' ')
    if scheme.lower()!='bearer' or not user_for(token):
        raise HTTPException(401,'Sign in to Linkabase.',headers={'WWW-Authenticate':'Bearer'})
    r=rows('SELECT project FROM diagrams WHERE id=?',(id,))
    if not r:raise HTTPException(404,'Drawing not found.')
    user=user_for(token)
    if not role_for(user,r[0]['project']):raise HTTPException(404,'Drawing not found.')
    try:return require(token,r[0]['project'],level)
    except PermissionError:raise HTTPException(403,'Your project access does not allow this action.')

async def drawing_body(request):
    """Reject large requests while reading, including chunked transfers."""
    length=request.headers.get('content-length')
    if length is not None:
        try:
            declared=int(length)
            if declared<0:raise ValueError()
        except ValueError:raise HTTPException(400,'Invalid Content-Length.')
        if declared>MAX_DRAWING_BYTES:raise HTTPException(413,'Drawing exceeds 25 MB')
    chunks=[];size=0
    async for chunk in request.stream():
        size+=len(chunk)
        if size>MAX_DRAWING_BYTES:raise HTTPException(413,'Drawing exceeds 25 MB')
        chunks.append(chunk)
    return b''.join(chunks)

@app.get('/api/drawings/{id}')
def load(id:str,request:Request):
    user=authorize(request,id)
    r=rows('SELECT scene,version,project FROM diagrams WHERE id=?',(id,))
    if not r: raise HTTPException(404)
    return {'scene':json.loads(r[0]['scene']),'version':r[0]['version'],'writable':role_for(user,r[0]['project']) in ('write','admin')}
@app.put('/api/drawings/{id}')
async def save(id:str,request:Request):
    authorize(request,id,'write')
    raw=await drawing_body(request)
    try:
        b=json.loads(raw)
        if not isinstance(b,dict):raise ValueError()
        scene=b['scene'];version=b['version']
        if not isinstance(scene,dict) or not isinstance(scene.get('elements'),list):raise ValueError()
        if type(version) is not int or not 0<=version<2**63:raise ValueError()
        if 'files' in scene and not isinstance(scene['files'],dict):raise ValueError()
        if 'appState' in scene and not isinstance(scene['appState'],dict):raise ValueError()
        png=base64.b64decode(b['preview'],validate=True) if b.get('preview') else None
        if png and not png.startswith(b'\x89PNG\r\n\x1a\n'): raise ValueError()
    except (ValueError,KeyError,TypeError,RecursionError): raise HTTPException(400,'Invalid drawing payload')
    with db() as c:
        changed=c.execute('UPDATE diagrams SET scene=?,preview=?,version=version+1 WHERE id=? AND version=?',(json.dumps(scene),png,id,version)).rowcount
        if not changed: raise HTTPException(409,'Drawing changed elsewhere. Reload before saving.')
    # Export native JSON for portability; database is authoritative.
    if re.fullmatch('[a-f0-9]{32}',id): (ROOT/'diagrams'/f'{id}.excalidraw').write_text(json.dumps(scene))
    return {'version':version+1}
