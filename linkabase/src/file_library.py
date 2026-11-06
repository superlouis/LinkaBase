"""Project file libraries: compact lists, drawing cards, and focused readers."""
import streamlit as st
from auth import require

def close_reader():
    st.session_state.pop('library_open',None)

def render_library(token,project,page,notes,items,view,topic_id=''):
    """view(child) retains the existing Wiki/drawing editor and authorization."""
    require(token,project)
    kind={'Wiki':'doc','Diagrams':'diagram'}[page]
    scoped=[c for c in items if c['kind']==kind and (not topic_id or c['note']==topic_id)]
    topics={n['id']:n['title'] for n in notes}
    def content(child,show_title=True):
        st.caption(topics.get(child['note'],'Topic'))
        if show_title:st.title(child['title'])
        view(child)
    full=st.session_state.get('library_full')
    if full:
        child=next((c for c in scoped if c['id']==full),None)
        if child:
            if st.button('Back to '+page,icon=':material/arrow_back:'):
                st.session_state.pop('library_full',None);st.rerun()
            content(child,show_title=False);return
        st.session_state.pop('library_full',None)
    st.caption({'Wiki':'Decisions, plans, and shared knowledge. Select a title to read.','Diagrams':'Project drawings, architecture diagrams, and process flows.'}[page])
    query=st.text_input('Search content',placeholder='Search '+page.lower()+'…',label_visibility='collapsed',key='library-search:'+page+project+topic_id)
    subset=[c for c in scoped if query.casefold() in c['title'].casefold()]
    st.caption(f'{len(subset)} of {len(scoped)} items')
    from library_surface import library_markup
    from surface import render_surface
    from auth import user_for
    theme=user_for(token)['theme']
    event=render_surface(library_markup(subset,kind,topics,project),'library:'+page+project,theme)
    if isinstance(event,dict) and event.get('kind')=='open' and event.get('id') in {c['id'] for c in subset}:
        if kind=='diagram':
            st.session_state.library_full=event['id'];st.rerun()
        else:st.session_state.library_open=event['id']
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
