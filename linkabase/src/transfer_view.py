"""Super-admin-only encrypted project import/export controls."""
import sqlite3
import time
from datetime import datetime,timezone
import streamlit as st
from auth import require_super_admin
from store import rows
from project_archive import export_project,import_project


def render_transfers(token):
    actor=require_super_admin(token)
    st.title('Project transfers')
    st.caption('Move one complete project in a password-encrypted archive. Super-admins only.')
    st.info('Exports include active topics, wiki pages and history, diagrams and images, tasks, and topic links. Accounts, passwords, sessions, permissions, and deleted content are excluded. Imports always create a new project.')
    export_tab,import_tab=st.tabs(['Export project','Import project'])
    with export_tab:
        projects=rows('SELECT id,name FROM projects ORDER BY name')
        if not projects:st.caption('Create a project before exporting.')
        else:
            with st.form('project-export',clear_on_submit=True):
                project=st.selectbox('Project to export',[p['id'] for p in projects],format_func=lambda id:next(p['name']+' · '+id for p in projects if p['id']==id))
                password=st.text_input('Archive password',type='password',help='At least 12 characters. Keep it somewhere safe; lost passwords cannot be recovered.')
                confirm=st.text_input('Confirm archive password',type='password')
                submitted=st.form_submit_button('Create encrypted export',type='primary')
            if submitted:
                st.session_state.pop('project_export',None)
                try:
                    if password!=confirm:raise ValueError('Archive passwords do not match.')
                    with st.spinner('Encrypting project…'):data=export_project(token,project,password)
                    st.session_state.project_export={'data':data,'project':project,'actor':actor['id'],'expires':time.time()+600}
                except (ValueError,PermissionError,OSError,sqlite3.DatabaseError) as error:st.error(str(error))
        prepared=st.session_state.get('project_export')
        if prepared and prepared['actor']==actor['id'] and prepared['expires']>time.time():
            require_super_admin(token)
            stamp=datetime.now(timezone.utc).strftime('%Y%m%d')
            st.download_button('Download encrypted project',prepared['data'],file_name=f"{prepared['project']}-{stamp}.lbproj",mime='application/octet-stream',type='primary')
            st.caption('AES-256-GCM encryption · scrypt password derivation · compressed contents · maximum 64 MiB encrypted / 256 MiB expanded. This format is opened through Linkabase Import, not a generic ZIP tool.')
            if st.button('Discard prepared export'):st.session_state.pop('project_export',None);st.rerun()
        elif prepared:st.session_state.pop('project_export',None)
    with import_tab:
        with st.form('project-import',clear_on_submit=True):
            upload=st.file_uploader('Encrypted project archive',type=['lbproj'],max_upload_size=64)
            password=st.text_input('Archive password to import',type='password')
            key=st.text_input('New project key',placeholder='IMPORT',help='2–10 uppercase letters/numbers, beginning with a letter. Existing projects are never overwritten.')
            name=st.text_input('Imported project name',placeholder='Keep original name if blank')
            submitted=st.form_submit_button('Import as new project',type='primary')
        if submitted:
            try:
                if upload is None:raise ValueError('Choose a Linkabase project archive.')
                with st.spinner('Validating and importing project…'):
                    imported=import_project(token,upload.getvalue(),password,key,name)
                st.success('Imported project '+imported+'. Select it from the project menu.')
            except (ValueError,PermissionError,OSError,sqlite3.DatabaseError) as error:st.error(str(error))
