"""Data-preserving upgrades for features removed from the active application."""
import json
import uuid
from store import now


def retire_storage(connection):
    """Archive removed-feature metadata; leave existing uploads untouched on disk."""
    has_assets = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='assets'").fetchone()
    records = [dict(row) for row in connection.execute('SELECT * FROM assets')] if has_assets else []
    children = [dict(row) for row in connection.execute("SELECT * FROM note_children WHERE kind='asset'")]
    if records or children:
        connection.execute('CREATE TABLE IF NOT EXISTS trash_entries(id TEXT PRIMARY KEY,project TEXT,kind TEXT,title TEXT,payload TEXT,deleted TEXT)')
        projects = {row['project'] for row in records + children}
        for project in projects:
            payload = {'assets': [row for row in records if row['project'] == project],
                       'children': [row for row in children if row['project'] == project]}
            connection.execute('INSERT INTO trash_entries VALUES (?,?,?,?,?,?)',
                               (uuid.uuid4().hex, project, 'retired_storage', 'Retired storage content', json.dumps(payload), now()))
    connection.execute("DELETE FROM note_children WHERE kind='asset'")
    if has_assets:
        connection.execute('DROP TABLE assets')
