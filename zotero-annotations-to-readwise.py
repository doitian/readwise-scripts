#!/usr/bin/env python3

from titlecase import titlecase
import json
import urllib.parse
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup


def get_items():
    with urlopen('http://127.0.0.1:23119/better-bibtex/cayw?selected=1&format=translate&translator=csljson') as resp:
        return json.loads(resp.read().decode('utf-8'))


def format_author(authors):
    return ' & '.join(
        a['literal'] if 'literal' in a else f'{a["given"]} {a["family"]}' for a in authors)


def collect_highlights(item, highlights):
    article = {
        'title': titlecase(item['title']),
        'author': format_author(item['author']),
        'source_url': f'zotero://select/library/items/{item["item-key"]}',
        'source_type': 'Zotero',
        'category': 'books' if item['type'] == 'book' else 'articles'
    }

    req = Request(
        'http://localhost:23119/better-bibtex/json-rpc',
        data=json.dumps({
            "jsonrpc": "2.0",
            "method": "item.notes",
            "params": [[item['id']]]
        }).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        method='POST',
    )
    with urlopen(req) as resp:
        notes = json.loads(resp.read().decode('utf-8'))['result'][item['id']]

    for note in notes:
        soup = BeautifulSoup(replace_br(note), 'html.parser')
        if soup.div is None:
            continue
        for p in soup.find_all('p'):
            highlight_tags = []
            for tag in p.select('span.highlight'):
                highlight_tags.append(tag.extract())
            for tag in p.select('span.citation'):
                tag.decompose()
            annotation = p.get_text(strip=True)
            highlights.append(format_highlight(
                article.copy(), highlight_tags, annotation))


def replace_br(html):
    return str(html).replace("<br/>", "\n").replace("<br>", "\n")


def get_highlight_text(highlight):
    text = BeautifulSoup(replace_br(highlight),
                         'html.parser').get_text().strip()
    if text.startswith('“') and text.endswith('”'):
        return text[1:-1]
    return text


def format_highlight(entry, highlight_tags, annotation):
    if len(highlight_tags) == 0:
        entry['text'] = annotation
        return entry

    entry['text'] = '…'.join(get_highlight_text(h) for h in highlight_tags)

    if annotation != '':
        if annotation.startswith('.') and '\n' not in annotation:
            entry['note'] = annotation + '\n'
        else:
            entry['note'] = annotation
    data = json.loads(urllib.parse.unquote(
        highlight_tags[0]['data-annotation']))
    item_key = data['attachmentURI'].split('/')[-1]
    entry['location_type'] = 'page'
    entry['location'] = int(data['pageLabel'])
    entry['highlight_url'] = f'zotero://open-pdf/library/items/{item_key}?page={data["position"]["pageIndex"]}&annotation={data["annotationKey"]}'

    return entry


def is_title(entry):
    return 'note' in entry and entry['note'] != '' and entry['note'].split()[0] in ['.h1', '.h2', '.h3']


def is_concatenating(entry):
    return 'note' in entry and entry['note'] != '' and entry['note'].split()[0] in ['.c1', '.c2', '.c3', '.c4', '.c5']


def concatenate_highlights(highlights):
    result = highlights[0]
    result['text'] = ' '.join(entry['text'] for entry in highlights)
    notes = []
    for entry in highlights:
        entry_note = entry['note'][3:].strip()
        if entry_note != '':
            notes.append(entry_note)
    if len(notes) > 0:
        result['note'] = "\n".join(notes)
    else:
        del result['note']

    return result


def squash_concatenating_highlights(highlights):
    pending_spans = []
    for entry in highlights:
        if is_concatenating(entry):
            if entry['note'].split()[0] == '.c1':
                if len(pending_spans) > 0:
                    yield concatenate_highlights(pending_spans)
                pending_spans = [entry]
            else:
                pending_spans.append(entry)
        else:
            if len(pending_spans) > 0:
                yield concatenate_highlights(pending_spans)
                pending_spans = []
            yield entry

    if len(pending_spans) > 0:
        yield concatenate_highlights(pending_spans)


def main(token, user_agent, dry_run=False):
    items = get_items()
    highlights = []
    for item in items:
        collect_highlights(item, highlights)

    highlights = list(squash_concatenating_highlights(highlights))

    if dry_run:
        print(json.dumps(highlights, indent=2))
        return

    req = Request(
        'https://readwise.io/api/v2/highlights/',
        headers={
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': user_agent
        },
        data=json.dumps({'highlights': highlights}).encode('utf-8'),
        method='POST',
    )
    urlopen(req)


if __name__ == '__main__':
    import sys
    import os

    dry_run = sys.argv[1] == '-n' if len(sys.argv) > 1 else False
    main(os.environ['READWISE_TOKEN'], os.environ['USER_AGENT'], dry_run)
