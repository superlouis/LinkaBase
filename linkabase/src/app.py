from pathlib import Path
import os,uuid,sqlite3,hashlib,re
import streamlit as st
from store import *
from auth import *
from notes import *
from ui import styling,footer,brand,eyebrow,breadcrumb,item_label,ICON,THEMES
from admin_views import render_admin,render_settings
from version import get_version
from projects import create_project
from project_views import render_project_settings
st.set_page_config(page_title='Linkabase',page_icon=str(ICON),layout='wide')
init();init_auth();init_notes()
from auth_view import render_auth
if not rows('SELECT id FROM users'):
 styling('Paper');render_auth(first_run=True);st.stop()
token=st.session_state.get('token','');user=user_for(token)
if not user:
 styling('Paper');render_auth();st.stop()
styling(user['theme'])
projects=[x for x in rows('SELECT * FROM projects ORDER BY id') if role_for(user,x['id'])]
st.session_state.setdefault('page','Highlight')
def go(page,note=None,child=None):
 st.session_state.pop('library_open',None);st.session_state.pop('library_full',None)
 st.session_state.page=page
 if page=='Topics' and note is None:
  st.session_state.pending_library_topic=''
  for key in ['selected_note','selected_child','pending_note','pending_child']:st.session_state.pop(key,None)
 if note is not None:
  st.session_state.selected_note=note;st.session_state.pending_note=note;st.session_state.pending_library_topic=note
 if child is not None:st.session_state.selected_child=child;st.session_state.pending_child=child
 st.session_state.pop('open_task',None);st.session_state.pop('delete_request',None);st.session_state.pop('delete_project',None)
def choose_library_topic(project):
 topic=st.session_state.get('library-topic:'+project,'')
 for key in ['library_open','library_full','selected_child','pending_child','open_task','delete_request']:
  st.session_state.pop(key,None)
 if topic:st.session_state.selected_note=topic
 else:st.session_state.pop('selected_note',None)
 st.session_state.pop('pending_note',None)

def nav(label,page,icon,active=None):
 selected=st.session_state.page==page if active is None else active
 st.button(label,icon=icon,width='stretch',type='primary' if selected else 'secondary',on_click=go,args=(page,),key='nav_'+page.replace(' ','_'))
with st.sidebar:
 brand();st.divider()
 if 'pending_project' in st.session_state:st.session_state['current-project']=st.session_state.pop('pending_project')
 p=st.selectbox('Project',[x['id'] for x in projects],format_func=lambda id:next(x['name'] for x in projects if x['id']==id),key='current-project') if projects else None
 if st.session_state.get('active_project')!=p:
  for key in ['open_task','selected_note','selected_child','pending_note','pending_child','pending_library_topic','board-event','delete_request','delete_project','library_open','library_full']:st.session_state.pop(key,None)
  st.session_state.active_project=p
 if p:
  topic_context=st.session_state.page=='Topics' and bool(st.session_state.get('selected_note'))
  active_kind=None
  if topic_context:
   selected_id=st.session_state.get('child-picker:'+st.session_state.selected_note,st.session_state.get('selected_child',''))
   active_content=rows('SELECT kind FROM note_children WHERE note=? AND project=? ORDER BY (id=?) DESC,kind,title LIMIT 1',(st.session_state.selected_note,p,selected_id))
   if active_content:active_kind=active_content[0]['kind']
  eyebrow('Project space');nav('Overview','Highlight',':material/space_dashboard:');nav('Tasks','Tasks',':material/task_alt:');nav('Topics','Topics',':material/layers:',active=st.session_state.page=='Topics' and not topic_context)
  require(token,p);sync_project(p)
  library_notes=list_notes(token,p);library_ids={n['id'] for n in library_notes}
  topic_key='library-topic:'+p
  if 'pending_library_topic' in st.session_state:
   pending=st.session_state.pop('pending_library_topic')
   st.session_state[topic_key]=pending if pending in library_ids else ''
  if st.session_state.get(topic_key,'') not in library_ids:st.session_state[topic_key]=''
  eyebrow('Library')
  library_topic=st.selectbox('Library topic',['']+[n['id'] for n in library_notes],
   format_func=lambda id:next((n['title'] for n in library_notes if n['id']==id),'All topics'),
   label_visibility='collapsed',key=topic_key,on_change=choose_library_topic,args=(p,))
  if library_topic and st.session_state.page=='Topics' and not st.session_state.get('selected_note'):
   st.session_state.selected_note=library_topic
  with st.container(key='library_tree'):
   nav('Wiki','Wiki',':material/article:',active=st.session_state.page=='Wiki' or active_kind=='doc');nav('Diagrams','Diagrams',':material/polyline:',active=st.session_state.page=='Diagrams' or active_kind=='diagram')
 eyebrow('Manage')
 nav('My preferences','Settings',':material/settings:')
 if p and role_for(user,p)=='admin':nav('Project settings','Project settings',':material/folder_managed:')
 if user['site_admin']:nav('Project transfers','Transfers',':material/import_export:')
 if st.button('Quick guide',icon=':material/help_outline:',width='stretch',key='quick-guide'):
  st.session_state.guide_requested=True
 if user['site_admin'] or (p and role_for(user,p)=='admin'):nav('Workspace administration' if user['site_admin'] else 'Project members','Administration',':material/group:')
 st.divider();st.caption(user['name']+' · '+('Super-admin' if user['site_admin'] else {'admin':'Project admin','write':'Writer','read':'Reader'}.get(role_for(user,p),'No project access')))
 with st.container(key='sidebar_account_actions'):
  if st.button('Sign out',icon=':material/logout:',width='stretch',key='sign_out'):
   logout(token);st.session_state.clear();st.rerun()
  if user['site_admin']:
   with st.popover('New project',icon=':material/add:',width='stretch',key='new_project'):
    with st.form('project'):
     name=st.text_input('Project name');key=st.text_input('Project key',placeholder='APP');desc=st.text_input('Description')
     if st.form_submit_button('Create project'):
      try:create_project(token,name,key,desc);st.session_state.pending_project=key;st.rerun()
      except (ValueError,PermissionError,sqlite3.IntegrityError) as e:st.error(str(e))
footer()
from onboarding import render_guide
render_guide(user,p)
page=st.session_state.page
if page not in {'Highlight','Tasks','Topics','Wiki','Diagrams','Settings','Administration','Project settings','Transfers'}:
 st.session_state.page='Highlight';st.rerun()
project_label=next((x['name'] for x in projects if x['id']==p),'Workspace')
if p and page in ['Wiki','Diagrams']:
 topic_label=next((n['title'] for n in library_notes if n['id']==library_topic),'All topics')
 breadcrumb(project_label,'Library',topic_label,page)
elif p and page=='Topics' and st.session_state.get('selected_note') in library_ids:
 breadcrumb(project_label,'Library',next(n['title'] for n in library_notes if n['id']==st.session_state.selected_note))
else:breadcrumb(project_label,{'Highlight':'Overview','Administration':'Members & access'}.get(page,page))
if page=='Settings':render_settings(token,user);st.caption('Linkabase v'+get_version());st.stop()
if page=='Administration':
 if not(user['site_admin'] or (p and role_for(user,p)=='admin')):st.error('Administrator access required.');st.stop()
 render_admin(token,user,p);st.stop()
if page=='Transfers':
 if not user['site_admin']:st.error('Super-admin access required.');st.stop()
 from transfer_view import render_transfers
 render_transfers(token);st.stop()
if page=='Project settings' and p:render_project_settings(token,p);st.stop()
if not p:
 if user['site_admin']:
  st.title('Create your first project');st.caption('Your workspace is empty. Add a project to start organizing topics, tasks, and documents.')
  with st.form('first-project'):
   name=st.text_input('Project name');key=st.text_input('Project key',placeholder='APP')
   if st.form_submit_button('Create project',type='primary'):
    try:create_project(token,name,key);st.session_state.pending_project=key;st.session_state.page='Highlight';st.rerun()
    except (ValueError,PermissionError,sqlite3.IntegrityError) as e:st.error(str(e))
 else:st.info('No projects assigned. Ask your administrator for access.')
 st.stop()
require(token,p)
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
  from diagram_view import render_diagram
  render_diagram(token,p,child,writable)

def close_task():
 st.session_state.pop('open_task',None);st.session_state.pop('new_task_target',None)
@st.dialog('Task',width='large',on_dismiss=close_task)
def task_dialog(id=None):
 guard('read');t=next((t for t in tasks if t['id']==id),None)
 if not writable:
  if not t:return
  st.subheader(t['title']);st.caption(t['id']+' · '+t['status']);st.markdown(t['description']);linked=targets.get(t['id'],'');st.caption(targetlabels.get(linked,'No linked topic'))
  if linked and st.button('Open linked topic'):
   go('Topics',note=linked.split(':',1)[1])
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
  options=list(targetlabels);current=targets.get(t['id'],'') if t else st.session_state.get('new_task_target','');target=st.selectbox('Linked topic',options,index=options.index(current) if current in options else 0,format_func=lambda k:targetlabels[k])
  if st.form_submit_button('Save task',type='primary'):
   guard()
   try:
    save_task(token,p,t['id'] if t else p+'-'+uuid.uuid4().hex[:6].upper(),dict(title=title,status=status,priority=priority,owner=owner,due=due,description=description),target,assignee=assignee);close_task();st.session_state.pop('new_task_target',None);st.rerun()
   except ValueError as e:st.error(str(e))
 if t and targets.get(t['id']):
  if st.button('Open linked topic',icon=':material/arrow_outward:'):
   go('Topics',note=targets[t['id']].split(':',1)[1])
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
@st.dialog({'Wiki':'Add Wiki','Diagrams':'Add Diagram'}.get(page,'Add content to a topic'),width='large',on_dismiss=close_content)
def content_dialog(kind):
 guard()
 if not notes:st.info('Create a topic first.');return
 if kind not in KINDS:kind='doc'
 if st.session_state.get('content-kind') not in KINDS:st.session_state.pop('content-kind',None)
 note=selector_notes(current=st.session_state.get('selected_note'))
 fixed_kind={'Wiki':'doc','Diagrams':'diagram'}.get(page)
 if fixed_kind:kind=fixed_kind
 else:kind=st.selectbox('Content type',list(KINDS),index=list(KINDS).index(kind),format_func=lambda x:KINDS[x],key='content-kind')
 with st.form('add-content'):
  title=st.text_input({'doc':'Wiki title','diagram':'Diagram title'}[kind] if fixed_kind else 'Content title')
  if kind=='doc':body=st.text_area('Markdown',height=220,placeholder='# Start writing…')
  if st.form_submit_button({'doc':'Add Wiki','diagram':'Add Diagram'}[kind] if fixed_kind else 'Add to topic',type='primary'):
   guard()
   try:
    if not title.strip():raise ValueError('Add a title.')
    if kind=='doc':
     ref=f'{p}/{uuid.uuid4().hex[:10]}-{re.sub(r"[^a-zA-Z0-9_-]","-",title.strip())[:60]}.md';save_doc(ref,body or '# '+title+'\n',digest(''),actor=user['name'])
    elif kind=='diagram':ref=new_diagram(p,title)
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
 st.caption('Tasks stay. Deleting a topic clears its task links; deleting individual content keeps the topic links. Local files and records are archived under workspace/trash. Recovery is manual in this version.')
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

selected_topic=next((n for n in notes if n['id']==st.session_state.get('selected_note')),None) if page=='Topics' else None
active_library_child=next((c for c in allchildren if c['id']==st.session_state.get('library_full') and c['kind']=={'Wiki':'doc','Diagrams':'diagram'}.get(page) and (not library_topic or c['note']==library_topic)),None) if page in ['Wiki','Diagrams'] else None
a,b=st.columns([6,1.2],vertical_alignment='center');a.title(active_library_child['title'] if active_library_child else selected_topic['title'] if selected_topic else 'Project overview' if page=='Highlight' else page)
if selected_topic:
 if b.button('Add content',type='primary',icon=':material/add:',disabled=not writable,width='stretch',key='note-add'):
  st.session_state.content_dialog='doc'
elif page in ['Topics','Wiki','Diagrams'] and not active_library_child:
 if b.button({'Topics':'New topic','Wiki':'Add Wiki','Diagrams':'Add Diagram'}[page],type='primary',icon=':material/add:',disabled=not writable,width='stretch',key='page-add-action'):
  if page=='Topics':st.session_state.note_dialog='new'
  else:st.session_state.content_dialog={'Wiki':'doc','Diagrams':'diagram'}[page]
elif page in ['Tasks','Highlight']:
 if b.button('New task',type='primary',icon=':material/add:',disabled=not writable,width='stretch',key='page-add-action'):st.session_state.open_task='new'

if page=='Highlight':
 from overview import render_overview
 render_overview(token,user,p,project,tasks,notes,allchildren,targets,targetlabels,go)
elif page=='Tasks':
 st.caption('Plan work, track progress, and keep related context close.')
 a,b,c=st.columns([4,1.3,1.5]);q=a.text_input('Search tasks',placeholder='Search tasks or assignees',label_visibility='collapsed');priority=b.selectbox('Priority',['All','High','Medium','Low'],label_visibility='collapsed');note_filter=c.selectbox('Topic filter',['']+[n['id'] for n in notes],format_func=lambda id:next((n['title'] for n in notes if n['id']==id),'All topics'),label_visibility='collapsed')
 def in_note(t):
  target=targets.get(t['id'],'')
  return not note_filter or target=='note:'+note_filter
 filtered=[t for t in tasks if q.lower() in (t['title']+' '+t['description']+' '+t['owner']).lower() and (priority=='All' or t['priority']==priority) and in_note(t)]
 st.caption(f'{len(filtered)} of {len(tasks)} tasks')
 view=st.radio('View',['Board','List'],horizontal=True,label_visibility='collapsed')
 component=Path(__file__).parent/'kanban'
 if view=='Board' and component.exists():
  from streamlit.components.v1 import declare_component
  board=declare_component('linkabase_kanban',path=str(component));event=board(tasks=[dict(t,context=targetlabels.get(targets.get(t['id'],''),'')) for t in filtered],statuses=STATUSES,writable=writable,colors=THEMES.get(user['theme'],THEMES['Midnight']),key='board:'+p,default=None)
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
 selected=selected_topic['id'] if selected_topic else None
 if not selected:
  st.caption('Group related documents, diagrams, and tasks.')
  search=st.text_input('Search topics',placeholder='Find a topic…',label_visibility='collapsed')
  found=[n for n in notes if search.lower() in n['title'].lower()]
  if notes and not found:st.info('No topics match your search.')
  else:
   from collections_ui import render_topics
   event=render_topics(found,allchildren,user['theme'],p)
   if isinstance(event,dict):
    if event.get('kind')=='topic' and event.get('id') in {n['id'] for n in found}:
     go('Topics',note=event['id']);st.rerun()
    elif event.get('kind')=='content':
     item=next((c for c in allchildren if c['id']==event.get('id')),None)
     if item:go('Topics',note=item['note'],child=item['id']);st.rerun()
 else:
  st.caption(f"{selected_topic['child_count']} connected items · Wiki pages and diagrams in this topic")
  with st.container(horizontal=True,vertical_alignment='center',key='topic_actions'):
   if st.button('All topics',icon=':material/arrow_back:',type='tertiary'):
    go('Topics');st.rerun()
   with st.container(horizontal=True,horizontal_alignment='right'):
    with st.popover('Topic options',icon=':material/more_horiz:',type='tertiary'):
     if st.button('Edit topic',disabled=not writable,icon=':material/edit:'):st.session_state.note_dialog=selected
     if st.button('Delete topic',disabled=not writable,icon=':material/delete:'):st.session_state.delete_request=('base',selected)
  subset=children(token,p,selected)
  linked=[t for t in tasks if targets.get(t['id'])=='note:'+selected]
  children_tab,tasks_tab=st.tabs(['Content · '+str(len(subset)),'Linked tasks · '+str(len(linked))])
  with children_tab:
   if not subset:st.info('Add a wiki page or drawing to this topic.')
   else:
    ids=[c['id'] for c in subset];current=st.session_state.get('selected_child')
    picker_key='child-picker:'+selected
    if current in ids and picker_key not in st.session_state:st.session_state[picker_key]=current
    with st.container(border=True,key='topic_content'):
     with st.container(horizontal=True,vertical_alignment='center',key='content_toolbar'):
      childid=st.selectbox('Content',ids,format_func=lambda id:next(KINDS[c['kind']]+' · '+c['title'] for c in subset if c['id']==id),key=picker_key,label_visibility='collapsed')
      with st.popover('Content options',icon=':material/more_horiz:',type='tertiary'):
       destination=selector_notes('Move to topic',key='move:'+childid,current=selected)
       if st.button('Move content',disabled=not writable or destination==selected):
        move_child(token,p,childid,destination);go('Topics',note=destination,child=childid);st.rerun()
       st.divider()
       if st.button('Delete content',disabled=not writable,icon=':material/delete:'):st.session_state.delete_request=('child',childid)
     st.session_state.selected_child=childid
     child=next(c for c in subset if c['id']==childid);child_view(child)
  with tasks_tab:
   if not linked:st.caption('Tasks linked to this topic appear here.')
   for t in linked:
    if st.button(t['title']+' · '+t['status'],key='linked:'+t['id']):st.session_state.open_task=t['id']
elif page in ['Wiki','Diagrams']:
 from file_library import render_library
 render_library(token,p,page,notes,allchildren,child_view,topic_id=library_topic)

if st.session_state.get('delete_request'):delete_dialog(*st.session_state.delete_request)
elif st.session_state.get('open_task'):
 requested=st.session_state.open_task
 if requested=='new' or requested in [t['id'] for t in tasks]:task_dialog(None if requested=='new' else requested)
elif st.session_state.get('note_dialog'):
 requested=st.session_state.note_dialog;note_dialog(None if requested=='new' else requested)
elif st.session_state.get('content_dialog'):content_dialog(st.session_state.content_dialog)
