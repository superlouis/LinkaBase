"""HTML document rows and diagram cards."""
from html import escape
import base64
from datetime import datetime, timezone
from store import ROOT, rows, safe
from surface import action


def library_markup(items, kind, topics, project):
    if kind not in {'doc','diagram'}:raise ValueError('Unsupported library type.')
    if not items:
        return '<div class="panel empty"><strong>Nothing here yet.</strong>Add content with the button above, or adjust your filters.</div>'
    if kind == 'diagram':
        cards = []
        for child in items:
            drawing = rows('SELECT preview FROM diagrams WHERE id=? AND project=?', (child['ref'],project))
            preview = drawing[0]['preview'] if drawing else None
            visual = ('<img alt="' + escape(child['title'], quote=True) + '" src="data:image/png;base64,' +
                      base64.b64encode(preview).decode() + '">') if preview else (
                      '<span class="placeholder"><span class="diagram-symbol">◇</span>Open to draw and save a preview</span>')
            cards.append('<article class="panel diagram-card">' + action(child['title'], 'open', child['id'], 'preview', visual) +
                         '<div class="diagram-info"><h3>' + escape(child['title']) + '</h3><p>' +
                         escape(topics.get(child['note'],'Topic')) + '</p><div class="card-foot"><span>Editable drawing</span>' +
                         action('Open drawing →','open',child['id']) + '</div></div></article>')
        return '<div class="topic-grid">' + ''.join(cards) + '</div>'
    html = '<section class="panel"><div class="row library-row" style="background:var(--paper)"><span class="section-label">' + 'Page' + '</span><span class="section-label">Topic</span><span class="section-label">' + 'Updated' + '</span></div>'
    for child in items:
        path = safe(ROOT/'docs',child['ref'])
        meta = datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).strftime('%b %d, %Y') if path.exists() else 'Missing file'
        icon = '▤'
        contents = ('<span class="name"><span class="topic-icon">' + icon + '</span><strong>' + escape(child['title']) + '</strong></span>' +
                    '<span class="type-label">' + escape(topics.get(child['note'],'Topic')) + '</span><span class="type-label">' + escape(meta) + '</span>')
        html += action(child['title'],'open',child['id'],'row library-row',contents)
    return html + '</section>'
