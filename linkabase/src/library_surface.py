"""HTML document rows and diagram cards."""
from html import escape
import base64
from datetime import datetime, timezone
from store import ROOT, rows, safe, digest
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
    metadata={row['path']:row for row in rows('SELECT * FROM wiki_authorship WHERE substr(path,1,?)=?',(len(project)+1,project+'/'))}
    html='<section class="panel"><div class="row library-row wiki-row"><span class="section-label">Page</span><span class="section-label topic-col">Topic</span><span class="section-label author-col">Author</span><span class="section-label editor-col">Last editor</span><span class="section-label">Updated</span></div>'
    for child in items:
        path=safe(ROOT/'docs',child['ref'])
        meta=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).strftime('%b %d, %Y') if path.exists() else 'Missing file'
        attribution=metadata.get(child['ref'],{})
        author=attribution.get('author','Unknown');editor=attribution.get('last_editor','Unknown')
        if attribution and path.is_file():
            try:
                if digest(path.read_text())!=attribution['content_digest']:editor='External edit'
            except (OSError,UnicodeError):editor='Unknown'
        contents=('<span class="name"><span class="topic-icon">▤</span><span><strong>'+escape(child['title'])+'</strong>'+
                  '<span class="mobile-authors">By '+escape(author)+' · Edited '+escape(editor)+'</span></span></span>'+
                  '<span class="type-label topic-col">'+escape(topics.get(child['note'],'Topic'))+'</span>'+
                  '<span class="type-label author-col" title="'+escape(author,quote=True)+'">'+escape(author)+'</span>'+
                  '<span class="type-label editor-col" title="'+escape(editor,quote=True)+'">'+escape(editor)+'</span>'+
                  '<span class="type-label">'+escape(meta)+'</span>')
        html+=action(child['title'],'open',child['id'],'row library-row wiki-row',contents)
    return html+'</section>'
