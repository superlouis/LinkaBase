"""An embedded drawing workspace with a compact, consistent toolbar."""
import os
import streamlit as st
from auth import require
from store import rows


def render_diagram(token,project,child,writable):
    require(token,project)
    found=rows('SELECT * FROM diagrams WHERE id=? AND project=?',(child['ref'],project))
    if not found:
        st.info('This drawing is no longer available.');return
    drawing=found[0]
    base=os.environ.get('EDITOR_PUBLIC_URL','http://localhost:8090').rstrip('/')
    url=base+'/editor/'+child['ref']+'#token='+token
    with st.container(key='diagram_toolbar',horizontal=True,vertical_alignment='center',gap='small'):
        mode=st.segmented_control('Diagram view',['Editor','Preview'],default='Editor',required=True,
                                  label_visibility='collapsed',key='diagram-mode:'+child['id'])
        with st.container(horizontal=True,horizontal_alignment='right',vertical_alignment='center'):
            st.link_button('Open in new tab',url,icon=':material/open_in_new:',type='tertiary')
            st.download_button('Download',drawing['scene'],file_name=drawing['title']+'.excalidraw',
                               mime='application/json',key='download:'+child['id'],icon=':material/download:',type='tertiary')
    if mode=='Editor':
        with st.container(key='diagram_canvas'):
            st.iframe(url,height=680,alt='Drawing editor: '+child['title'])
        st.caption('Save changes in the drawing toolbar.' if writable else 'Read-only drawing · your project role does not allow edits.')
    else:
        @st.fragment(run_every='3s')
        def preview():
            require(token,project)
            current=rows('SELECT preview,version FROM diagrams WHERE id=? AND project=?',(child['ref'],project))
            if not current:st.info('This drawing is no longer available.');return
            if current[0]['preview']:
                with st.container(key='diagram_preview'):st.image(current[0]['preview'],width='stretch')
                st.caption(f"Saved version {current[0]['version']} · preview updates automatically")
            else:st.info('No saved preview yet. Open Editor and save your drawing to create one.')
        preview()
