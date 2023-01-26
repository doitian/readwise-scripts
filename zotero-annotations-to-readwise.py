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
        soup = BeautifulSoup(note, 'html.parser')
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


def get_highlight_text(highlight):
    text = BeautifulSoup(str(highlight).replace(
        "<br/>", "\n"), 'html.parser').get_text().strip()
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


def main(token, dry_run=False):
    items = get_items()
    highlights = []
    for item in items:
        collect_highlights(item, highlights)

    if dry_run:
        print(json.dumps(highlights, indent=2))
        return

    req = Request(
        'https://readwise.io/api/v2/highlights/',
        headers={
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        data=json.dumps({'highlights': highlights}).encode('utf-8'),
        method='POST',
    )
    urlopen(req)


if __name__ == '__main__':
    import sys
    import os

    dry_run = sys.argv[1] == '-n' if len(sys.argv) > 1 else False
    main(os.environ['READWISE_TOKEN'], dry_run)
