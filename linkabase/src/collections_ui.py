"""Topic collection cards, rendered with the same layout as the HTML concept."""
from html import escape
from surface import action


def topic_markup(notes, content):
    if not notes:
        return '<div class="panel empty"><strong>No topics yet.</strong>Create a topic to collect related documents and diagrams.</div>'
    cards = []
    symbols = {'doc':'▤','diagram':'◇'}
    for index, note in enumerate(notes):
        subset = sorted((c for c in content if c['note'] == note['id']),
                        key=lambda c: ({'doc':0,'diagram':1}[c['kind']], c['title'].casefold()))
        counts = [(label, sum(c['kind'] == kind for c in subset)) for kind, label in [('doc','page'),('diagram','diagram')]]
        summary = ' · '.join(f'{count} {label}{"s" if count!=1 else ""}' for label,count in counts if count) or 'Ready for your first content'
        card = (f'<article class="panel topic-card"><span class="topic-icon {"blue" if index%2 else ""}">▱</span>' +
                action(note['title'], 'topic', note['id'], 'card-title') +
                '<p class="topic-summary">' + escape(summary) + '</p><div class="subitems">')
        for child in subset[:2]:
            card += action(child['title'], 'content', child['id'], 'text-link',
                           symbols[child['kind']] + ' &nbsp; ' + escape(child['title']))
        if not subset: card += '<span class="muted">Wiki pages and diagrams belong here.</span>'
        card += '<div style="flex:1"></div></div><div class="card-foot"><span>' + str(note['child_count']) + (' connected item</span>' if note['child_count']==1 else ' connected items</span>') + action('Open topic →','topic',note['id']) + '</div></article>'
        cards.append(card)
    return '<div class="topic-grid">' + ''.join(cards) + '</div>'


def render_topics(notes, content, theme, project):
    from surface import render_surface
    return render_surface(topic_markup(notes, content), 'topics-gallery:' + project, theme)
