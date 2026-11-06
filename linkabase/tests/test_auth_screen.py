"""Setup/sign-in behavior and version metadata regression checks."""
import _bootstrap
import os,tempfile,tomllib
from pathlib import Path
from unittest.mock import patch
os.environ['WORKSPACE_DIR']=tempfile.mkdtemp()
from store import rows
from auth import user_for
from version import get_version
import version
from streamlit.testing.v1 import AppTest

with (_bootstrap.PROJECT/'pyproject.toml').open('rb') as source:
    expected=tomllib.load(source)['project']['version']
assert get_version()==expected
with tempfile.TemporaryDirectory() as tmp:
    metadata=Path(tmp)/'pyproject.toml'
    metadata.write_text('[project]\nversion="9.8.7"\n')
    with patch.object(version,'PYPROJECT',metadata):
        assert get_version()=='9.8.7'
        metadata.write_text('[project]\nversion="9.8.8"\n')
        assert get_version()=='9.8.8'
    with patch.object(version,'PYPROJECT',Path(tmp)/'missing.toml'),patch.object(version,'installed_version',return_value='7.6.5'):
        assert get_version()=='7.6.5'

app=AppTest.from_file(str(_bootstrap.PROJECT/'src/app.py'),default_timeout=30).run()
assert not app.exception
assert app.title[0].value=='Make yourself at home.'
next(t for t in app.text_input if t.label=='Full name').set_value('New Owner')
next(t for t in app.text_input if t.label=='Email').set_value('owner@example.com')
next(t for t in app.text_input if t.label=='Password').set_value('password-12345')
next(t for t in app.text_input if t.label=='Confirm password').set_value('different-password')
next(b for b in app.button if b.label=='Create super-admin').click().run()
assert not app.exception and app.error and not rows('SELECT id FROM users')
next(t for t in app.text_input if t.label=='Confirm password').set_value('password-12345')
next(b for b in app.button if b.label=='Create super-admin').click().run()
assert not app.exception and user_for(app.session_state.token)['site_admin']
next(b for b in app.sidebar.button if b.label=='Sign out').click().run()
assert not app.exception and app.title[0].value=='Welcome back.'
assert not app.sidebar.button
next(t for t in app.text_input if t.label=='Email').set_value('owner@example.com')
next(t for t in app.text_input if t.label=='Password').set_value('incorrect-password')
next(b for b in app.button if b.label=='Sign in').click().run()
assert not app.exception and app.error
next(t for t in app.text_input if t.label=='Password').set_value('password-12345')
next(b for b in app.button if b.label=='Sign in').click().run()
assert not app.exception and user_for(app.session_state.token)['name']=='New Owner'
assert app.title[0].value=='Create your first project'
print('PASS: metadata version updates, initial setup, validation, sign-out, failed/successful sign-in')
