"""A welcoming sign-in and setup screen with a locally animated illustration."""
from html import escape
from pathlib import Path
import sqlite3
import streamlit as st
from auth import create_user, login
from ui import ICON, logo_image
from version import get_version

ASSETS = Path(__file__).parent / 'components'


@st.cache_resource
def _story_renderer():
    story=(ASSETS / 'auth_story.html').read_text().replace('<!-- BRAND_MARK -->',ICON.read_text())
    return st.components.v2.component('linkabase_auth_story',html=story,css=(ASSETS / 'auth.css').read_text())

def render_auth(first_run=False):
    st.html('<style>' + (ASSETS / 'auth.css').read_text() + '</style>')
    with st.container(key='auth_shell'):
        left, right = st.columns([1.12, 1], gap=None, vertical_alignment='center')
        with left:
            _story_renderer()(key='auth-story',height='content')
        with right, st.container(key='auth_form'):
            st.html('<div class="auth-form-mark">' + logo_image() + '</div><div class="auth-eyebrow">YOUR WORKSPACE</div>')
            st.title('Make yourself at home.' if first_run else 'Welcome back.')
            st.caption('Create your first account to get started.' if first_run else 'Good to see you. Sign in to pick up where you left off.')
            with st.form('bootstrap' if first_run else 'login', border=False):
                if first_run: name = st.text_input('Full name', placeholder='Your name', autocomplete='name')
                email = st.text_input('Email', placeholder='you@example.com', autocomplete='email')
                password = st.text_input('Password', type='password', autocomplete='new-password' if first_run else 'current-password')
                if first_run:
                    st.caption('Use at least 12 characters.')
                    confirm = st.text_input('Confirm password', type='password', autocomplete='new-password')
                submitted = st.form_submit_button('Create super-admin' if first_run else 'Sign in', type='primary', width='stretch')
            if submitted:
                try:
                    if first_run:
                        if password != confirm: raise ValueError('Passwords do not match.')
                        create_user(name, email, password, bootstrap=True)
                    st.session_state.token = login(email, password)
                    st.rerun()
                except (ValueError, sqlite3.IntegrityError) as error:
                    st.error(str(error))
            st.html('<div class="auth-reassurance"><span aria-hidden="true">◇</span> A little less scattered. A lot more connected.</div>')
    st.html('<div class="auth-footer"><span>Linkabase · v' + escape(get_version()) + '</span><span>Your workspace. Self-hosted.</span></div>')
