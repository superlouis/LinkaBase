import streamlit as st
from store import rows
from auth import require
from projects import rename_project,delete_project,project_counts

def close_project_delete():st.session_state.pop('delete_project',None)
@st.dialog('Delete project',width='large',on_dismiss=close_project_delete)
def confirm_project_delete(token,project):
    require(token,project,'admin')
    row=rows('SELECT * FROM projects WHERE id=?',(project,))
    if not row:close_project_delete();st.rerun()
    project_row=row[0];counts=project_counts(token,project)
    st.subheader('Delete '+project_row['name']+'?')
    st.write('This removes the project, its tasks, topics, wiki pages, drawings, files, and project memberships from the active workspace.')
    st.caption(' · '.join(str(n)+' '+label for label,n in counts.items()))
    st.caption('Local files and records are archived under workspace/trash for manual recovery. User accounts are not deleted.')
    with st.form('confirm-project-deletion'):
        confirm=st.text_input('Type the project key to confirm',placeholder=project)
        a,b=st.columns(2)
        submit=a.form_submit_button('Delete project and contents',type='primary',icon=':material/delete:')
        cancel=b.form_submit_button('Cancel')
    if cancel:close_project_delete();st.rerun()
    if submit:
        if confirm!=project:st.error('The project key does not match. Nothing was deleted.');return
        try:
            delete_project(token,project);close_project_delete()
            for key in ['current-project','active_project','selected_note','selected_child','pending_note','pending_child','open_task','note_dialog','content_dialog','delete_request','board-event']:st.session_state.pop(key,None)
            st.session_state.page='Highlight';st.rerun()
        except (PermissionError,ValueError,OSError) as e:st.error(str(e))

def render_project_settings(token,project):
    require(token,project,'admin')
    r=rows('SELECT * FROM projects WHERE id=?',(project,))
    if not r:st.info('This project no longer exists.');return
    project_row=r[0]
    st.title('Project settings');st.caption(project_row['name']+' · '+project)
    with st.container(border=True):
        st.subheader('Project details')
        with st.form('rename-project'):
            name=st.text_input('Project name',project_row['name'])
            st.caption('The project key stays the same, preserving content and task links.')
            if st.form_submit_button('Save project name',type='primary'):
                try:rename_project(token,project,name);st.rerun()
                except (ValueError,PermissionError) as e:st.error(str(e))
    with st.container(border=True):
        st.subheader('Delete project');st.caption('Remove this project and all its contents. A confirmation is required.')
        if st.button('Delete project',icon=':material/delete:'):st.session_state.delete_project=project
    if st.session_state.get('delete_project')==project:confirm_project_delete(token,project)
