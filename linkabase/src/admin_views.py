import streamlit as st
from store import *
from auth import *
from ui import THEMES
import sqlite3

def render_settings(token,user):
    st.title('Settings');st.caption('Manage your profile and appearance.')
    with st.container(border=True):
     st.subheader('Your profile')
     a,b=st.columns(2);a.text_input('Full name',value=user['name'],disabled=True);b.text_input('Email address',value=user['email'],disabled=True)
     st.caption('Super-admin' if user['site_admin'] else 'Project member')
    with st.container(border=True):
     st.subheader('Appearance');theme=st.selectbox('Theme',list(THEMES),index=list(THEMES).index(user['theme']) if user['theme'] in THEMES else 0)
     st.caption('Midnight is the default dark workspace design. Your theme preference applies across the app.')
     if st.button('Apply theme',type='primary'):execute('UPDATE users SET theme=? WHERE id=?',(theme,user['id']));st.rerun()
    with st.expander('Change your password'):
     with st.form('password'):
      old=st.text_input('Current password',type='password');new=st.text_input('New password (12+ characters)',type='password');confirm=st.text_input('Confirm new password',type='password')
      if st.form_submit_button('Change password'):
       try:
        verify=login(user['email'],old);logout(verify)
        if new!=confirm:raise ValueError('Passwords do not match.')
        hashed=password_hash(new)
        with db() as c:
         c.execute('UPDATE users SET password=? WHERE id=?',(hashed,user['id']));c.execute('DELETE FROM sessions WHERE user=?',(user['id'],))
        st.session_state.clear();st.rerun()
       except ValueError as e:st.error(str(e))

def render_admin(token,user,p):
    if not user_for(token) or not (user_for(token)['site_admin'] or (p and role_for(user_for(token),p)=='admin')):raise PermissionError('Administrator access required.')
    st.title('Workspace administration' if user['site_admin'] else 'Project members');st.caption('Give each person exactly the access they need.')
    if user['site_admin']:
     with st.expander('＋ Create user'):
      with st.form('user'):
       name=st.text_input('Full name');email=st.text_input('Email');password=st.text_input('Initial password (12+ characters)',type='password')
       if st.form_submit_button('Create account',type='primary'):
        try:create_user(name,email,password);st.success('Account created. Assign project access below.')
        except (ValueError,sqlite3.IntegrityError) as e:st.error(str(e))
     st.subheader('Accounts')
     accounts=rows('SELECT id,name,email,active,site_admin FROM users ORDER BY name')
     st.dataframe([{'Name':a['name'],'Email':a['email'],'Role':'Super-admin' if a['site_admin'] else 'Project member','Active':bool(a['active'])} for a in accounts],hide_index=True,width='stretch')
     target=st.selectbox('Account to manage',[a['id'] for a in accounts],format_func=lambda id,accounts=accounts:next(a['email'] for a in accounts if a['id']==id))
     selected=next(a for a in accounts if a['id']==target)
     with st.expander('Workspace role'):
      st.caption('Super-admins can create projects and manage every project. Project admins receive access below, per project.')
      elevated=st.checkbox('Super-admin',value=bool(selected['site_admin']),key='super:'+target)
      if st.button('Save workspace role'):
       try:set_super_admin(token,target,elevated);st.rerun()
       except (ValueError,PermissionError) as e:st.error(str(e))
     if not selected['site_admin']:
      if st.button('Disable account' if selected['active'] else 'Enable account'):
       execute('UPDATE users SET active=? WHERE id=?',(int(not selected['active']),target));execute('DELETE FROM sessions WHERE user=?',(target,));st.rerun()
      with st.expander('Reset account password'):
       reset=st.text_input('New account password',type='password')
       if st.button('Reset password'):
        try:execute('UPDATE users SET password=? WHERE id=?',(password_hash(reset),target));execute('DELETE FROM sessions WHERE user=?',(target,));st.success('Password reset; active sessions revoked.')
        except ValueError as e:st.error(str(e))
    if p:
     require(token,p,'admin');st.subheader('Project access · '+p)
     members=rows('SELECT u.name,u.email,m.role FROM memberships m JOIN users u ON u.id=m.user WHERE m.project=?',(p,))
     st.dataframe(members,hide_index=True,width='stretch')
     st.caption('Read: view and download · Write: create and edit · Admin: write + manage project membership. Super-admins have access to all projects.')
     accounts=rows('SELECT id,name,email FROM users WHERE site_admin=0 AND active=1 ORDER BY name')
     if accounts:
      with st.form('member'):
       member=st.selectbox('User',[a['id'] for a in accounts],format_func=lambda id,accounts=accounts:next(a['name']+' · '+a['email'] for a in accounts if a['id']==id))
       access=st.selectbox('Access',['read','write','admin','Remove access'],format_func=lambda x:{'read':'Reader','write':'Writer','admin':'Project admin'}.get(x,x))
       if st.form_submit_button('Save access',type='primary'):
        require(token,p,'admin')
        if access=='Remove access':execute('DELETE FROM memberships WHERE user=? AND project=?',(member,p))
        else:execute('INSERT OR REPLACE INTO memberships VALUES (?,?,?)',(member,p,access))
        st.rerun()
