"""uv run python manage.py {start,stop,restart,status,logs,run}."""
import argparse,json,os,socket,subprocess,sys,time
from pathlib import Path
import psutil
from dotenv import load_dotenv
from filelock import FileLock
BASE=Path(__file__).resolve().parent
load_dotenv(BASE/'.env',override=False)
RUNTIME=Path(os.environ.get('LINKABASE_RUNTIME_DIR',str(BASE/'.runtime'))).resolve()
STATE=RUNTIME/'processes.json'
def records():
 try:return json.loads(STATE.read_text())
 except (FileNotFoundError,json.JSONDecodeError):return {}
def process(rec):
 try:
  p=psutil.Process(rec['pid'])
  return p if abs(p.create_time()-rec['created'])<.01 and p.status()!=psutil.STATUS_ZOMBIE else None
 except (psutil.Error,KeyError):return None
def stop_locked():
 for name,rec in records().items():
  p=process(rec)
  if p:
   try:
    group=p.children(recursive=True)+[p]
    for x in reversed(group):
     try:x.terminate()
     except psutil.Error:pass
    _,alive=psutil.wait_procs(group,timeout=5)
    for x in alive:
     try:x.kill()
     except psutil.Error:pass
   except psutil.Error:pass
   print(name+': stopped')
 STATE.unlink(missing_ok=True)
def start_locked():
 old=records()
 if old and all(process(rec) for rec in old.values()) and len(old)==2:
  print('Linkabase is already running.');return
 if old:stop_locked()
 host=os.environ.get('LINKABASE_HOST','127.0.0.1');port=int(os.environ.get('LINKABASE_PORT','8501'));editor=int(os.environ.get('LINKABASE_EDITOR_PORT','8090'))
 if port==editor:raise RuntimeError('App and editor ports must differ.')
 for value in [port,editor]:
  try:
   with socket.socket() as s:s.bind((host,value))
  except OSError as e:raise RuntimeError(f'Port {value} is occupied. Stop the existing service or change the ports in .env.') from e
 env=os.environ.copy();env.setdefault('WORKSPACE_DIR',str(BASE/'workspace'));env.setdefault('EDITOR_PUBLIC_URL',f'http://localhost:{editor}')
 commands={'drawing-studio':[sys.executable,'-m','uvicorn','editor_api:app','--host',host,'--port',str(editor)],'linkabase':[sys.executable,'-m','streamlit','run',str(BASE/'app.py'),'--server.address='+host,'--server.port='+str(port),'--server.headless=true','--browser.gatherUsageStats=false']}
 launched={}
 try:
  for name,command in commands.items():
   with (RUNTIME/(name+'.log')).open('ab') as output:
    proc=subprocess.Popen(command,cwd=BASE,env=env,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
   try:created=psutil.Process(proc.pid).create_time()
   except psutil.Error:
    proc.terminate()
    raise RuntimeError('Cannot track '+name+' process identity. Check logs and host process permissions.')
   launched[name]={'pid':proc.pid,'created':created}
   STATE.write_text(json.dumps(launched));STATE.chmod(0o600)
  time.sleep(1)
  if not all(process(rec) for rec in launched.values()):raise RuntimeError('A service exited. Run the logs command to inspect the startup error.')
 except BaseException:
  stop_locked();raise
 print(f'Linkabase started: http://{host}:{port}')
 if not (Path(env.get('EDITOR_DIST_DIR',str(BASE/'editor_dist')))/'index.html').exists():print('Drawing editor assets are not in this source patch. Keep editor_dist/ from your existing installation for Excalidraw.')
def main():
 parser=argparse.ArgumentParser(description='Linkabase lifecycle manager');parser.add_argument('command',choices=['start','stop','restart','status','logs','run','storage']);parser.add_argument('--lines',type=int,default=40);args=parser.parse_args()
 if args.command=='storage':
  workspace=Path(os.environ.get('WORKSPACE_DIR',str(BASE/'workspace'))).expanduser().resolve()
  print('Workspace: '+str(workspace));print('Database: '+str(workspace/'work.sqlite'));print('Exists: '+str(workspace.exists()));return
 RUNTIME.mkdir(parents=True,exist_ok=True)
 try:
  if args.command=='logs':
   for name in ['linkabase','drawing-studio']:
    path=RUNTIME/(name+'.log');print('\n'+name+'\n')
    if path.exists():print('\n'.join(path.read_text(errors='replace').splitlines()[-max(1,args.lines):]))
   return
  with FileLock(str(RUNTIME/'lifecycle.lock'),timeout=10):
   if args.command=='status':
    state=records()
    if not state:print('Linkabase is stopped.')
    for name,rec in state.items():print(name+(': running' if process(rec) else ': stopped'))
   elif args.command=='stop':stop_locked()
   else:
    if args.command=='restart':stop_locked()
    start_locked()
  if args.command=='run':
   print('Press Ctrl+C to stop both services.')
   try:
    while True:
     time.sleep(1)
     if not all(process(rec) for rec in records().values()) or not records():break
   finally:
    with FileLock(str(RUNTIME/'lifecycle.lock'),timeout=10):stop_locked()
 except KeyboardInterrupt:pass
 except Exception as e:print(str(e),file=sys.stderr);raise SystemExit(1)
if __name__=='__main__':main()
