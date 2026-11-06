from pathlib import Path
import os,uuid,sqlite3,hashlib,re
import streamlit as st
from store import *
from auth import *
from notes import *
from ui import styling,footer,brand,eyebrow,ICON,THEMES
from admin_views import render_admin,render_settings
from version import __version__
from projects import create_project
from project_views import render_project_settings
st.set_page_config(page_title='Linkabase',page_icon=str(ICON),layout='wide')
init();init_auth();init_notes()
if not rows('SELECT id FROM users'):
 styling();footer();st.title('Welcome to Linkabase');st.caption('Create your super-admin account. Existing data stays in place.')
 with st.form('bootstrap'):
  name=st.text_input('Full name');email=st.text_input('Email');pw=st.text_input('Password',type='password');confirm=st.text_input('Confirm password',type='password')
  if st.form_submit_button('Create super-admin',type='primary'):
   try:
    if pw!=confirm:raise ValueError('Passwords do not match.')
    create_user(name,email,pw,bootstrap=True);st.session_state.token=login(email,pw);st.rerun()
   except (ValueError,sqlite3.IntegrityError) as e:st.error(str(e))
 st.stop()
token=st.session_state.get('token','');user=user_for(token)
if not user:
 styling();footer();a,b,c=st.columns([1,1.4,1])
 with b:
  st.image(str(ICON),width=54);st.title('Welcome back.');st.caption('Sign in to Linkabase.')
  with st.form('login'):
   email=st.text_input('Email');pw=st.text_input('Password',type='password')
   if st.form_submit_button('Sign in',type='primary',width='stretch'):
    try:st.session_state.token=login(email,pw);st.rerun()
    except ValueError as e:st.error(str(e))
 st.stop()
styling(user['theme']);footer()
projects=[x for x in rows('SELECT * FROM projects ORDER BY id') if role_for(user,x['id'])]
st.session_state.setdefault('page','Highlight')
def go(page,note=None,child=None):
 st.session_state.pop('library_open',None);st.session_state.pop('library_full',None)
 st.session_state.page=page
 if note is not None:st.session_state.selected_note=note;st.session_state.pending_note=note
 if child is not None:st.session_state.selected_child=child;st.session_state.pending_child=child
 st.session_state.pop('open_task',None);st.session_state.pop('delete_request',None);st.session_state.pop('delete_project',None)
def nav(label,page,icon):
 st.button(label,icon=icon,width='stretch',type='primary' if st.session_state.page==page else 'secondary',on_click=go,args=(page,),key='nav_'+page.replace(' ','_'))
with st.sidebar:
 brand();st.divider()
 if 'pending_project' in st.session_state:st.session_state['current-project']=st.session_state.pop('pending_project')
 p=st.selectbox('Project',[x['id'] for x in projects],format_func=lambda id:next(x['name'] for x in projects if x['id']==id),key='current-project') if projects else None
 if st.session_state.get('active_project')!=p:
  for key in ['open_task','selected_note','selected_child','board-event','delete_request','delete_project','library_open','library_full']:st.session_state.pop(key,None)
  st.session_state.active_project=p
 if p:
  eyebrow('Workspace');nav('Overview','Highlight',':material/space_dashboard:');nav('Tasks','Tasks',':material/task_alt:');nav('Topics','Topics',':material/layers:')
  with st.expander('Files',expanded=True,icon=':material/folder_open:'):
   nav('Wiki','Wiki',':material/article:');nav('Diagrams','Diagrams',':material/polyline:');nav('Storage','Storage',':material/hard_drive:')
 with st.expander('Settings',expanded=st.session_state.page in ['Settings','Administration','Project settings'],icon=':material/tune:'):
  nav('My preferences','Settings',':material/settings:')
  if p and role_for(user,p)=='admin':nav('Project settings','Project settings',':material/folder_managed:')
  if user['site_admin'] or (p and role_for(user,p)=='admin'):nav('Workspace administration' if user['site_admin'] else 'Project members','Administration',':material/group:')
 st.divider();st.caption(user['name']+' · '+('Super-admin' if user['site_admin'] else {'admin':'Project admin','write':'Writer','read':'Reader'}.get(role_for(user,p),'No project access')))
 if st.button('Sign out',icon=':material/logout:',width='stretch'):
  logout(token);st.session_state.clear();st.rerun()
 if user['site_admin']:
  with st.expander('New project',icon=':material/add:'):
   with st.form('project'):
    name=st.text_input('Project name');key=st.text_input('Project key',placeholder='APP');desc=st.text_input('Description')
    if st.form_submit_button('Create project'):
     try:create_project(token,name,key,desc);st.session_state.pending_project=key;st.rerun()
     except (ValueError,PermissionError,sqlite3.IntegrityError) as e:st.error(str(e))
page=st.session_state.page
if page=='Settings':render_settings(token,user);st.caption('Linkabase v'+__version__);st.stop()
if page=='Administration':
 if not(user['site_admin'] or (p and role_for(user,p)=='admin')):st.error('Administrator access required.');st.stop()
 render_admin(token,user,p);st.stop()
if page=='Project settings' and p:render_project_settings(token,p);st.stop()
if not p:
 if user['site_admin']:
  st.title('Create your first project');st.caption('Your workspace is empty. Add a project to start organizing topics, tasks, and files.')
  with st.form('first-project'):
   name=st.text_input('Project name');key=st.text_input('Project key',placeholder='APP')
   if st.form_submit_button('Create project',type='primary'):
    try:create_project(token,name,key);st.session_state.pending_project=key;st.session_state.page='Highlight';st.rerun()
    except (ValueError,PermissionError,sqlite3.IntegrityError) as e:st.error(str(e))
 else:st.info('No projects assigned. Ask your administrator for access.')
 st.stop()
require(token,p);sync_project(p)
if 'pending_note' in st.session_state:st.session_state['note-picker:'+p]=st.session_state.pop('pending_note')
if 'pending_child' in st.session_state and st.session_state.get('selected_note'):st.session_state['child-picker:'+st.session_state.selected_note]=st.session_state.pop('pending_child')
writable=LEVEL[role_for(user,p)]>=2
project=next(x for x in projects if x['id']==p)
notes=list_notes(token,p);allchildren=children(token,p)
tasks=rows('SELECT * FROM tasks WHERE project=? ORDER BY id',(p,));targets=task_targets(p);targetlabels=target_choices(token,p)

def guard(level='write'):
 try:require(token,p,level)
 except PermissionError as e:st.error(str(e));st.stop()

def selector_notes(label='Parent topic',key=None,current=None):
 ids=[n['id'] for n in notes]
 if not ids:return None
 return st.selectbox(label,ids,index=ids.index(current) if current in ids else 0,format_func=lambda id:next(n['title'] for n in notes if n['id']==id),key=key)

def child_view(child):
 guard('read')
 if child['kind']=='doc':
  path=safe(ROOT/'docs',child['ref'])
  if not path.exists():st.warning('This file is missing from the vault.');return
  from wiki import render_wiki
  render_wiki(token,p,child,path,writable,user['theme'])
 elif child['kind']=='diagram':
  base=os.environ.get('EDITOR_PUBLIC_URL','http://localhost:8090').rstrip('/');url=base+'/editor/'+child['ref']+'#token='+token
  st.link_button('Edit in Excalidraw' if writable else 'Open in Excalidraw',url,type='primary',icon=':material/open_in_new:')
  if st.checkbox('Edit here',key='embed:'+child['id']):st.iframe(url,height=640)
  @st.fragment(run_every='3s')
  def preview():
   guard('read');r=rows('SELECT * FROM diagrams WHERE id=? AND project=?',(child['ref'],p))
   if not r:st.warning('Drawing not found.');return
   d=r[0]
   if d['preview']:st.image(d['preview'],width='stretch')
   else:st.caption('Save a drawing in the studio to generate its preview.')
   st.download_button('Download editable drawing',d['scene'],file_name=d['title']+'.excalidraw',mime='application/json',key='download:'+child['id']);st.caption('Saved version '+str(d['version']))
  preview()
 else:
  r=rows('SELECT * FROM assets WHERE id=? AND project=?',(child['ref'],p))
  if not r:st.warning('File not found.');return
  f=r[0];st.caption(f'{f["size"]:,} bytes' if f['size'] else 'External storage link')
  if f['path'].startswith('https://'):st.link_button('Open storage link',f['path'],icon=':material/open_in_new:')
  else:
   path=safe(ROOT,f['path'])
   if path.exists():st.download_button('Download file',path.read_bytes(),file_name=f['name'],key='file:'+child['id'],type='primary')
   else:st.warning('Attachment is missing from disk.')

def close_task():
 st.session_state.pop('open_task',None);st.session_state.pop('new_task_target',None)
@st.dialog('Task',width='large',on_dismiss=close_task)
def task_dialog(id=None):
 guard('read');t=next((t for t in tasks if t['id']==id),None)
 if not writable:
  if not t:return
  st.subheader(t['title']);st.caption(t['id']+' · '+t['status']);st.markdown(t['description']);linked=targets.get(t['id'],'');st.caption(targetlabels.get(linked,'No linked topic'))
  if linked and st.button('Open linked content'):
   kind,ref=linked.split(':',1)
   if kind=='note':go('Topics',note=ref)
   else:
    child=next(x for x in allchildren if x['id']==ref);go('Topics',note=child['note'],child=ref)
   close_task();st.rerun()
  return
 with st.form('task-dialog'):
  title=st.text_input('Title',t['title'] if t else '')
  a,b=st.columns(2);status=a.selectbox('Status',STATUSES,index=STATUSES.index(t['status']) if t else 0);priority=b.selectbox('Priority',['High','Medium','Low'],index=['High','Medium','Low'].index(t['priority']) if t else 1)
  a,b=st.columns(2)
  people=project_users(token,p);people_by_id={u['id']:u for u in people};assignment=rows('SELECT user FROM task_assignees WHERE task=?',(t['id'],)) if t else []
  current=assignment[0]['user'] if assignment and assignment[0]['user'] in people_by_id else ''
  if not current and t and t['owner']:
   matches=[u['id'] for u in people if u['name']==t['owner']]
   current=matches[0] if len(matches)==1 else '__legacy__'
  choices=['']+list(people_by_id)
  if current=='__legacy__':choices.append('__legacy__')
  labels={'':'Unassigned',**{u['id']:u['name']+' · '+u['email'] for u in people}}
  if t:labels['__legacy__']=t['owner']+' (previous assignment)'
  assignee=a.selectbox('Assignee',choices,index=choices.index(current),format_func=lambda id:labels[id])
  initial_due=None
  if t and t['due']:
   try:initial_due=datetime.strptime(t['due'],'%Y-%m-%d').date()
   except ValueError:pass
  due_date=b.date_input('Due date',value=initial_due,format='YYYY-MM-DD',min_value=__import__('datetime').date(1900,1,1),max_value=__import__('datetime').date(2100,12,31))
  due=due_date.isoformat() if due_date else ''
  owner=people_by_id[assignee]['name'] if assignee in people_by_id else (t['owner'] if t and assignee=='__legacy__' else '')
  description=st.text_area('Description',t['description'] if t else '',height=160)
  options=list(targetlabels);current=targets.get(t['id'],'') if t else st.session_state.get('new_task_target','');target=st.selectbox('Linked topic or child',options,index=options.index(current) if current in options else 0,format_func=lambda k:targetlabels[k])
  if st.form_submit_button('Save task',type='primary'):
   guard()
   try:
    save_task(token,p,t['id'] if t else p+'-'+uuid.uuid4().hex[:6].upper(),dict(title=title,status=status,priority=priority,owner=owner,due=due,description=description),target,assignee=assignee);close_task();st.session_state.pop('new_task_target',None);st.rerun()
   except ValueError as e:st.error(str(e))
 if t and targets.get(t['id']):
  if st.button('Open linked topic / content',icon=':material/arrow_outward:'):
   kind,ref=targets[t['id']].split(':',1)
   if kind=='note':go('Topics',note=ref)
   else:
    child=next(x for x in allchildren if x['id']==ref);go('Topics',note=child['note'],child=ref)
   close_task();st.rerun()

def close_note():st.session_state.pop('note_dialog',None)
@st.dialog('Topic',width='large',on_dismiss=close_note)
def note_dialog(id=None):
 guard();n=next((n for n in notes if n['id']==id),None)
 with st.form('note-details'):
  title=st.text_input('Topic title',n['title'] if n else '')
  if st.form_submit_button('Save topic',type='primary'):
   try:
    guard()
    if n:edit_note(token,p,n['id'],title,n['summary']);new=n['id']
    else:new=create_note(token,p,title)
    close_note();go('Topics',note=new);st.rerun()
   except ValueError as e:st.error(str(e))

def close_content():
 st.session_state.pop('content_dialog',None);st.session_state.pop('content-kind',None)
@st.dialog({'Wiki':'Add Wiki','Diagrams':'Add Diagram','Storage':'Add Storage'}.get(page,'Add content to a topic'),width='large',on_dismiss=close_content)
def content_dialog(kind):
 guard()
 if not notes:st.info('Create a topic first.');return
 note=selector_notes(current=st.session_state.get('selected_note'))
 fixed_kind={'Wiki':'doc','Diagrams':'diagram','Storage':'asset'}.get(page)
 if fixed_kind:kind=fixed_kind
 else:kind=st.selectbox('Content type',list(KINDS),index=list(KINDS).index(kind),format_func=lambda x:KINDS[x],key='content-kind')
 with st.form('add-content'):
  title=st.text_input({'doc':'Wiki title','diagram':'Diagram title','asset':'Storage title'}[kind] if fixed_kind else 'Content title')
  if kind=='doc':body=st.text_area('Markdown',height=220,placeholder='# Start writing…')
  elif kind=='asset':
   mode=st.radio('Storage type',['Upload file','External link'],horizontal=True);upload=st.file_uploader('File');url=st.text_input('HTTPS link',placeholder='https://…')
  if st.form_submit_button({'doc':'Add Wiki','diagram':'Add Diagram','asset':'Add Storage'}[kind] if fixed_kind else 'Add to topic',type='primary'):
   guard()
   try:
    if not title.strip():raise ValueError('Add a title.')
    if kind=='doc':
     ref=f'{p}/{uuid.uuid4().hex[:10]}-{re.sub(r"[^a-zA-Z0-9_-]","-",title.strip())[:60]}.md';save_doc(ref,body or '# '+title+'\n',digest(''))
    elif kind=='diagram':ref=new_diagram(p,title)
    else:
     ref=uuid.uuid4().hex
     if mode=='Upload file':
      if upload is None:raise ValueError('Choose a file to upload.')
      name=Path(upload.name).name;relative='attachments/'+ref+'_'+name;safe(ROOT,relative).write_bytes(upload.getbuffer());size=upload.size
     else:
      if not url.startswith('https://'):raise ValueError('Use an HTTPS storage link.')
      name=title;relative=url;size=0
     execute('INSERT INTO assets VALUES (?,?,?,?,?,?)',(ref,p,name,relative,size,''))
    child=add_child(token,p,note,kind,ref,title);close_content();go('Topics',note=note,child=child);st.rerun()
   except ValueError as e:st.error(str(e))

def close_delete():st.session_state.pop('delete_request',None)
@st.dialog('Confirm deletion',width='large',on_dismiss=close_delete)
def delete_dialog(kind,id):
 guard()
 item=next((n for n in notes if n['id']==id),None) if kind=='base' else next((x for x in allchildren if x['id']==id),None)
 if not item:close_delete();st.rerun()
 st.subheader('Delete '+item['title']+'?')
 if kind=='base':
  contents=children(token,p,id)
  st.write(f'This removes the topic and all {len(contents)} content items inside it.')
  for child in contents:st.caption(KINDS[child['kind']]+' · '+child['title'])
 else:st.write('This removes only this content item. Its parent topic stays.')
 st.caption('Linked tasks stay; their deleted-content links are removed. Local files and records are archived under workspace/trash. External storage files are not deleted. Recovery is manual in this version.')
 a,b=st.columns(2)
 if a.button('Delete topic and contents' if kind=='base' else 'Delete content',type='primary',icon=':material/delete:'):
  try:
   delete_content(token,p,id,whole_base=kind=='base');close_delete()
   for key in ['selected_child','pending_child']:st.session_state.pop(key,None)
   if kind=='base':
    for key in ['selected_note','pending_note','note-picker:'+p]:st.session_state.pop(key,None)
   else:
    st.session_state.selected_note=item['note'];st.session_state.pending_note=item['note'];st.session_state.pop('child-picker:'+item['note'],None)
   st.session_state.page='Topics';st.rerun()
  except (ValueError,OSError) as e:st.error(str(e))
 if b.button('Cancel'):close_delete();st.rerun()

eyebrow(project['name']+' / '+('Overview' if page=='Highlight' else page))
a,b=st.columns([5,1.4],vertical_alignment='center');a.title('Overview' if page=='Highlight' else page)
if page in ['Topics','Wiki','Diagrams','Storage']:
 if b.button({'Topics':'New topic','Wiki':'Add Wiki','Diagrams':'Add Diagram','Storage':'Add Storage'}[page],type='primary',icon=':material/add:',disabled=not writable,width='stretch'):
  if page=='Topics':st.session_state.note_dialog='new'
  else:st.session_state.content_dialog={'Wiki':'doc','Diagrams':'diagram','Storage':'asset'}[page]
elif page=='Tasks':
 if b.button('New task',type='primary',icon=':material/add:',disabled=not writable,width='stretch'):st.session_state.open_task='new'

if page=='Highlight':
 st.caption(project['description'])
 a,b,c,d=st.columns(4);a.metric('Open tasks',sum(t['status']!='Done' for t in tasks));b.metric('In progress',sum(t['status']=='In progress' for t in tasks));c.metric('Topics',len(notes));d.metric('Linked content',len(allchildren))
 l,r=st.columns([1.6,1],gap='large')
 with l:
  st.subheader('Your next moves')
  for t in [t for t in tasks if t['status']!='Done'][:6]:
   with st.container(border=True):
    a,b=st.columns([4,1]);a.markdown('**'+t['title']+'**');a.caption(t['status']+' · '+t['priority']+' · '+targetlabels.get(targets.get(t['id'],''),'No linked topic'))
    if b.button('Open',key='highlight:'+t['id']):st.session_state.open_task=t['id']
 with r:
  st.subheader('Project topics')
  for n in notes[:5]:
   with st.container(border=True):
    st.markdown('**'+n['title']+'**');st.caption(str(n['child_count'])+' content items')
    st.button('Explore topic',key='highlight-note:'+n['id'],on_click=go,args=('Topics',n['id']))
  done=sum(t['status']=='Done' for t in tasks);st.progress(done/max(len(tasks),1),text=f'{done} of {len(tasks)} tasks complete')
elif page=='Tasks':
 a,b,c=st.columns([4,1.3,1.5]);q=a.text_input('Search tasks',placeholder='Search tasks or assignees',label_visibility='collapsed');priority=b.selectbox('Priority',['All','High','Medium','Low'],label_visibility='collapsed');note_filter=c.selectbox('Topic filter',['']+[n['id'] for n in notes],format_func=lambda id:next((n['title'] for n in notes if n['id']==id),'All topics'),label_visibility='collapsed')
 def in_note(t):
  target=targets.get(t['id'],'')
  return not note_filter or target=='note:'+note_filter or any(target=='child:'+c['id'] and c['note']==note_filter for c in allchildren)
 filtered=[t for t in tasks if q.lower() in (t['title']+' '+t['description']+' '+t['owner']).lower() and (priority=='All' or t['priority']==priority) and in_note(t)]
 view=st.radio('View',['Board','List'],horizontal=True,label_visibility='collapsed')
 component=Path(__file__).parent/'kanban'
 if view=='Board' and component.exists():
  from streamlit.components.v1 import declare_component
  board=declare_component('linkabase_kanban',path=str(component));event=board(tasks=filtered,statuses=STATUSES,writable=writable,colors=THEMES[user['theme']],key='board:'+p,default=None)
  st.caption('Drag to move. Click to open. Use List for a keyboard-friendly view.')
  if event and event.get('nonce')!=st.session_state.get('board-event'):
   st.session_state['board-event']=event.get('nonce')
   if event.get('id') in [t['id'] for t in tasks]:
    if event.get('action')=='open':st.session_state.open_task=event['id']
    elif event.get('action')=='move' and event.get('status') in STATUSES:
     guard();execute('UPDATE tasks SET status=? WHERE id=? AND project=?',(event['status'],event['id'],p));st.rerun()
 else:
  for t in filtered:
   with st.container(border=True):
    a,b,c=st.columns([4,2,1]);a.markdown('**'+t['title']+'**');a.caption(t['id']+' · '+targetlabels.get(targets.get(t['id'],''),'No linked topic'));b.caption(t['status']+' · '+t['priority'])
    if c.button('Open',key=t['id']):st.session_state.open_task=t['id']
elif page=='Topics':
 st.caption('A topic brings related wiki pages, drawings, and files together. Tasks can link to the topic or to one child.')
 search=st.text_input('Search topics',placeholder='Find a topic or collection',label_visibility='collapsed')
 found=[n for n in notes if search.lower() in n['title'].lower()]
 if not found:st.info('Create a topic to start organizing your project.')
 else:
  l,r=st.columns([1,5],gap='medium')
  with l:
   current=st.session_state.get('selected_note');ids=[n['id'] for n in found]
   selected=st.radio('Topics',ids,index=ids.index(current) if current in ids else 0,format_func=lambda id:next(n['title'] for n in found if n['id']==id),key='note-picker:'+p)
   st.session_state.selected_note=selected
  with r:
   n=next(n for n in notes if n['id']==selected);st.subheader(n['title'])
   a,b,c=st.columns([1.3,1.2,3])
   if a.button('Add content',type='primary',disabled=not writable,key='note-add',icon=':material/add:'):st.session_state.content_dialog='doc'
   if b.button('Edit topic',disabled=not writable,icon=':material/edit:'):st.session_state.note_dialog=selected
   if c.button('Delete topic',disabled=not writable,icon=':material/delete:'):st.session_state.delete_request=('base',selected)
   children_tab,tasks_tab=st.tabs(['Content · '+str(n['child_count']),'Linked tasks'])
   with children_tab:
    subset=children(token,p,selected)
    if not subset:st.info('Add a wiki doc, drawing, or file to this topic.')
    else:
     ids=[c['id'] for c in subset];current=st.session_state.get('selected_child');content_column,delete_column=st.columns([5,1.4],vertical_alignment='bottom');childid=content_column.selectbox('Content',ids,index=ids.index(current) if current in ids else 0,format_func=lambda id:next(KINDS[c['kind']]+' · '+c['title'] for c in subset if c['id']==id),key='child-picker:'+selected)
     if delete_column.button('Delete content',disabled=not writable,icon=':material/delete:'):st.session_state.delete_request=('child',childid)
     child=next(c for c in subset if c['id']==childid);child_view(child)
     with st.expander('Organize this content'):
      destination=selector_notes('Move to topic',key='move:'+childid,current=selected)
      if st.button('Move content',disabled=not writable or destination==selected):move_child(token,p,childid,destination);go('Topics',note=destination,child=childid);st.rerun()
   with tasks_tab:
    linked=[t for t in tasks if targets.get(t['id'])=='note:'+selected or any(targets.get(t['id'])=='child:'+c['id'] for c in children(token,p,selected))]
    if not linked:st.caption('Tasks linked to this topic or its children appear here.')
    for t in linked:
     if st.button(t['title']+' · '+t['status'],key='linked:'+t['id']):st.session_state.open_task=t['id']
elif page in ['Wiki','Diagrams','Storage']:
 from file_library import render_library
 render_library(token,p,page,notes,allchildren,child_view)

if st.session_state.get('delete_request'):delete_dialog(*st.session_state.delete_request)
elif st.session_state.get('open_task'):
 requested=st.session_state.open_task
 if requested=='new' or requested in [t['id'] for t in tasks]:task_dialog(None if requested=='new' else requested)
elif st.session_state.get('note_dialog'):
 requested=st.session_state.note_dialog;note_dialog(None if requested=='new' else requested)
elif st.session_state.get('content_dialog'):content_dialog(st.session_state.content_dialog)
