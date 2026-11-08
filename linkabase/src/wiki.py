"""Read-first wiki with a locally bundled visual editor and optimistic saves."""
from pathlib import Path
import hashlib
import streamlit as st
from streamlit.components.v1 import declare_component
from auth import require
from store import ROOT,save_doc,digest
from ui import THEMES
editor=declare_component('linkabase_wiki',path=str(Path(__file__).parent/'wiki_editor'))
def render_wiki(token,project,child,path,writable,theme):
    key='wiki:'+child['id'];editing=st.session_state.get(key+':editing',False)
    if editing and writable:
        if key+':original' not in st.session_state:
            st.session_state[key+':original']=path.read_text()
            st.session_state[key+':revision']=0
        original=st.session_state[key+':original']
        st.caption('Edit document · changes stay in this editor until you save.')
        event=editor(content=original,revision=st.session_state[key+':revision'],colors=THEMES.get(theme,THEMES['Midnight']),key=key+':editor',default=None)
        if event and event['nonce']!=st.session_state.get(key+':event'):
            st.session_state[key+':event']=event['nonce']
            if event['action']=='save':
                actor=require(token,project,'write')
                try:
                    save_doc(child['ref'],event['content'],digest(original),actor=actor['name'])
                    st.session_state[key+':saved']=True
                except ValueError as e:st.error(str(e));return
            st.session_state[key+':editing']=False
            st.session_state.pop(key+':original',None);st.rerun()
        return
    a,b=st.columns([5,1])
    a.caption('Wiki · '+child['title'])
    if b.button('Edit',icon=':material/edit:',disabled=not writable,key=key+':edit',width='stretch'):
        st.session_state[key+':editing']=True;st.session_state.pop(key+':original',None);st.rerun()
    if st.session_state.pop(key+':saved',False):st.success('Saved just now.')
    @st.fragment(run_every='3s')
    def live():
        require(token,project)
        try:text=path.read_text()
        except FileNotFoundError:st.info('This document was moved or deleted. Refresh to update.');return
        with st.container(border=True,key='wikireader_'+child['id']):st.markdown(text)
        st.caption('Live document · updates from your vault every 3 seconds')
    live()
    with st.expander('Version history',icon=':material/history:'):
        folder=ROOT/'history'/hashlib.sha256(child['ref'].encode()).hexdigest()
        versions=sorted(folder.glob('*.md'),key=lambda f:f.stat().st_mtime,reverse=True) if folder.exists() else []
        if not versions:st.caption('Previous versions appear after the first save.')
        for i,f in enumerate(versions[:20]):
            with st.expander('Revision '+str(len(versions)-i)):
                st.code(f.read_text(),language='markdown');st.download_button('Download revision',f.read_bytes(),file_name=path.name,key=str(f))
