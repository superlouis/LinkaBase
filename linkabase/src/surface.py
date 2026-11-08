"""Small HTML surfaces with Streamlit event routing and isolated styles."""
from pathlib import Path
from html import escape
import streamlit as st
from ui import THEMES

ASSETS = Path(__file__).parent / 'components'

@st.cache_resource
def _renderer():
    return st.components.v2.component(
        'linkabase_workspace_surface',
        html='<div id="surface"></div>',
        css=(ASSETS / 'workspace.css').read_text(),
        js=(ASSETS / 'workspace.js').read_text(),
    )


def render_surface(markup, key, theme='Midnight'):
    result = _renderer()(data={'html': markup, 'colors': THEMES.get(theme, THEMES['Midnight'])},
                         key=key, on_action_change=lambda: None)
    return result.action


def action(label, kind, id='', css='text-link', contents=None):
    """Only application-generated markup belongs in contents; escape all user data."""
    return (f'<button type="button" class="{escape(css, quote=True)}" '
            f'data-action="{escape(kind, quote=True)}" data-id="{escape(id, quote=True)}" aria-label="{escape(label, quote=True)}">'
            + (contents if contents is not None else escape(label)) + '</button>')


def initials(name):
    return escape(''.join(word[0] for word in name.split()[:2]).upper() or '—')
