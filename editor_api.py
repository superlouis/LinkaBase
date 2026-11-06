import json, base64, re, os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from store import init,db,rows,ROOT
from auth import init_auth,require,role_for
app=FastAPI(title='Linkabase drawing service')
init();init_auth()
DIST=Path(os.environ.get('EDITOR_DIST_DIR',str(Path(__file__).with_name('editor_dist')))).resolve()
if DIST.exists(): app.mount('/studio-assets', StaticFiles(directory=DIST), name='studio-assets')
@app.get('/health')
def health(): return {'ok':True}
@app.get('/editor/{id}',response_class=HTMLResponse)
def editor(id:str):
    if not rows('SELECT id FROM diagrams WHERE id=?',(id,)): raise HTTPException(404)
    if not (DIST/'index.html').exists(): raise HTTPException(503,'Editor assets missing. Build the frontend or rebuild the Docker image.')
    return HTMLResponse((DIST/'index.html').read_text(),headers={'Referrer-Policy':'no-referrer','Cache-Control':'no-store'})
def authorize(request,id,level='read'):
    r=rows('SELECT project FROM diagrams WHERE id=?',(id,))
    if not r:raise HTTPException(404)
    token=request.headers.get('authorization','').removeprefix('Bearer ')
    try:return require(token,r[0]['project'],level)
    except PermissionError:raise HTTPException(403,'Sign in to Linkabase with the required project access.')
@app.get('/api/drawings/{id}')
def load(id:str,request:Request):
    user=authorize(request,id)
    r=rows('SELECT scene,version,project FROM diagrams WHERE id=?',(id,))
    if not r: raise HTTPException(404)
    return {'scene':json.loads(r[0]['scene']),'version':r[0]['version'],'writable':role_for(user,r[0]['project']) in ('write','admin')}
@app.put('/api/drawings/{id}')
async def save(id:str,request:Request):
    authorize(request,id,'write')
    raw=await request.body()
    if len(raw)>25*1024*1024: raise HTTPException(413,'Drawing exceeds 25 MB')
    try:
        b=json.loads(raw);scene=b['scene'];version=int(b['version'])
        if not isinstance(scene.get('elements'),list): raise ValueError()
        png=base64.b64decode(b['preview'],validate=True) if b.get('preview') else None
        if png and not png.startswith(b'\x89PNG\r\n\x1a\n'): raise ValueError()
    except (ValueError,KeyError,TypeError): raise HTTPException(400,'Invalid drawing payload')
    with db() as c:
        changed=c.execute('UPDATE diagrams SET scene=?,preview=?,version=version+1 WHERE id=? AND version=?',(json.dumps(scene),png,id,version)).rowcount
        if not changed: raise HTTPException(409,'Drawing changed elsewhere. Reload before saving.')
    # Export native JSON for portability; database is authoritative.
    if re.fullmatch('[a-f0-9]{32}',id): (ROOT/'diagrams'/f'{id}.excalidraw').write_text(json.dumps(scene))
    return {'version':version+1}
