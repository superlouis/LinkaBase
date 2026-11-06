"""Project file libraries: compact lists, drawing cards, and focused readers."""
import mimetypes
from pathlib import Path
from datetime import datetime,timezone
import streamlit as st
from auth import require
from store import ROOT,rows,safe

def close_reader():
    st.session_state.pop('library_open',None)

def storage_preview(token,project,child):
    require(token,project)
    found=rows('SELECT * FROM assets WHERE id=? AND project=?',(child['ref'],project))
    if not found:st.warning('File no longer exists.');return
    asset=found[0]
    if asset['path'].startswith('https://'):
        st.caption('External storage link');st.link_button('Open link',asset['path'],icon=':material/open_in_new:');return
    path=safe(ROOT,asset['path'])
    if not path.is_file():st.warning('Attachment is missing from disk.');return
    mime=mimetypes.guess_type(asset['name'])[0] or 'application/octet-stream'
    st.caption(f"{asset['name']} · {path.stat().st_size:,} bytes")
    st.download_button('Download file',path.read_bytes(),file_name=asset['name'],mime=mime,type='primary',key='library-download:'+child['id'])
    suffix=Path(asset['name']).suffix.lower()
    try:
        if mime.startswith('image/') and suffix!='.svg':st.image(path.read_bytes(),width='stretch')
        elif suffix=='.pdf' and hasattr(st,'pdf'):st.pdf(path.read_bytes())
        elif suffix in {'.txt','.md','.csv','.json','.yaml','.yml','.log','.py','.toml'}:
            if path.stat().st_size>256_000:st.info('This text file is large. Download it to view the complete file.')
            else:st.code(path.read_text(encoding='utf-8'),language={'.json':'json','.py':'python','.yaml':'yaml','.yml':'yaml','.md':'markdown'}.get(suffix,'text'))
        else:st.info('Preview is unavailable for this file type. Download it to open locally.')
    except (UnicodeError,ValueError,RuntimeError):st.info('This file could not be previewed. Download it to open locally.')

def render_library(token,project,page,notes,items,view):
    """view(child) retains the existing Wiki/drawing editor and authorization."""
    require(token,project)
    kind={'Wiki':'doc','Diagrams':'diagram','Storage':'asset'}[page]
    scoped=[c for c in items if c['kind']==kind]
    topics={n['id']:n['title'] for n in notes}
    def content(child):
        st.caption(topics.get(child['note'],'Topic'))
        st.title(child['title'])
        if kind=='asset':storage_preview(token,project,child)
        else:view(child)
    full=st.session_state.get('library_full')
    if full:
        child=next((c for c in scoped if c['id']==full),None)
        if child:
            if st.button('Back to '+page,icon=':material/arrow_back:'):
                st.session_state.pop('library_full',None);st.rerun()
            content(child);return
        st.session_state.pop('library_full',None)
    st.caption({'Wiki':'Decisions, plans, and shared knowledge. Select a title to read.','Diagrams':'Your project at a glance. Open a drawing to explore or edit it.','Storage':'Project files and external links. Select a file to preview or download.'}[page])
    a,b=st.columns([3,1])
    query=a.text_input('Search content',placeholder='Search '+page.lower()+'…',label_visibility='collapsed',key='library-search:'+page+project)
    parent=b.selectbox('Parent topic',['']+list(topics),format_func=lambda id:topics.get(id,'All topics'),label_visibility='collapsed',key='library-filter:'+page+project)
    subset=[c for c in scoped if query.casefold() in c['title'].casefold() and (not parent or c['note']==parent)]
    st.caption(f'{len(subset)} items');st.divider()
    if not subset:st.info('No items found. Add content or adjust your filters.')
    elif kind=='diagram':
        for start in range(0,len(subset),3):
            columns=st.columns(3)
            for col,child in zip(columns,subset[start:start+3]):
                with col,st.container(border=True):
                    drawing=rows('SELECT * FROM diagrams WHERE id=? AND project=?',(child['ref'],project))
                    with st.container(height=180,border=False):
                        if drawing and drawing[0]['preview']:st.image(drawing[0]['preview'],width='stretch')
                        else:st.caption('Drawing preview');st.markdown('### ◇');st.caption('Save in Excalidraw to generate a thumbnail.')
                    if st.button(child['title'],icon=':material/polyline:',key='library-item:'+child['id'],width='stretch'):st.session_state.library_open=child['id']
                    st.caption(topics.get(child['note'],'Topic'))
    else:
        a,b,c=st.columns([5,2,1.5]);a.caption('PAGE' if kind=='doc' else 'FILE');b.caption('TOPIC');c.caption('UPDATED' if kind=='doc' else 'SIZE / TYPE')
        for child in subset:
            with st.container(key='libraryrow_'+child['id']):
                a,b,c=st.columns([5,2,1.5],vertical_alignment='center')
                if a.button(child['title'],icon=':material/article:' if kind=='doc' else ':material/attach_file:',key='library-item:'+child['id'],width='stretch'):st.session_state.library_open=child['id']
                b.caption(topics.get(child['note'],'Topic'))
                if kind=='doc':
                    path=safe(ROOT/'docs',child['ref'])
                    c.caption(datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).strftime('%b %d, %Y') if path.exists() else 'Missing file')
                else:
                    asset=rows('SELECT * FROM assets WHERE id=? AND project=?',(child['ref'],project))
                    c.caption(('External link' if asset[0]['path'].startswith('https://') else f"{asset[0]['size']:,} bytes") if asset else 'Missing file')
    @st.dialog('Project content',width='large',on_dismiss=close_reader)
    def reader(id):
        require(token,project)
        child=next((c for c in scoped if c['id']==id),None)
        if not child:st.info('Content no longer exists.');return
        a,b=st.columns([4,1.5]);a.caption(page.upper())
        if b.button('Full page',icon=':material/open_in_full:',width='stretch'):
            st.session_state.library_full=id;close_reader();st.rerun()
        content(child)
    # Creation and task dialogs take priority; Streamlit allows one dialog at a time.
    if st.session_state.get('library_open') and not any(st.session_state.get(k) for k in ['content_dialog','note_dialog','open_task','delete_request']):reader(st.session_state.library_open)
