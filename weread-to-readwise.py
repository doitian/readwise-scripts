#!/usr/bin/env python3

import fileinput
import json
from urllib.request import urlopen, Request


# Example:
#
# ```
# 《虚像的丑角》
# 东野圭吾
# https://weread.qq.com/web/bookDetail/43132e60813ab7439g011388
# 2个笔记
#
# .h1 第三章听心
#
# .h2 4
#
# >> 倾听别人的意见，不断检验自己的做法、想法是否正确，这无论对肉体还是精神来说都是很大的负担。相比之下，不听别人的意见，固执地坚持自己的想法就很轻松。贪图轻松的人就是懒汉，我说错了吗？
#
# https://weread.qq.com/web/reader/43132e60813ab7439g011388k02e32f0021b02e74f10ece8#1
#
# .h1 第四章曲球
#
# .h2 7
#
# >> 您所说的抵抗，在我看来是令人钦佩的努力。我认为努力不会白费，即使在棒球上没能取得成果，今后也必定会发挥作用
# ```
# https://weread.qq.com/web/reader/43132e60813ab7439g011388kd67323c0227d67d8ab4fb04#2
def collect_highlights(lines):
    seen_highlight_urls = set()

    article = {
        'title': None,
        'author': None,
        'source_url': None,
        'source_type': 'Weread',
        'category': 'books'
    }
    result = []
    pending_article = None
    for line in lines:
        line = line.strip()
        if line == '':
            continue

        if line.startswith('《') and line.endswith('》'):
            article['title'] = line[1:-1]
        elif article['author'] is None:
            article['author'] = line
        elif article['source_url'] is None and line.startswith('https://'):
            article['source_url'] = line
        elif line.startswith('.h1 ') or line.startswith('.h2 ') or line.startswith('.h3 '):
            if pending_article is not None:
                result.append(pending_article)
            pending_article = article.copy()
            pending_article['text'] = line[4:]
            pending_article['note'] = line[:3]
            result.append(pending_article)
            pending_article = None
        elif line.startswith('>> '):
            if pending_article is None:
                pending_article = article.copy()
            if pending_article is not None:
                pending_article['text'] = line[3:]
            else:
                raise RuntimeError('expect pending article')
        elif line.startswith('https://'):
            if pending_article is not None:
                pending_article['highlight_url'] = line
                if line in seen_highlight_urls:
                    raise RuntimeError('duplicated highlight url: ' + line)
                seen_highlight_urls.add(line)
            else:
                raise RuntimeError('expect pending article')
        elif pending_article is not None:
            raise RuntimeError('unexpected line: ' + line)

    if pending_article is not None:
        result.append(pending_article)
    return result

def main(token, args):
    dry_run = args[1] == '-n' if len(sys.argv) > 1 else False
    input_args = args[1:] if not dry_run else args[2:]
    highlights = collect_highlights(fileinput.input(input_args))

    if dry_run:
        print(json.dumps(highlights, indent=2, ensure_ascii=False))
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

    main(os.environ['READWISE_TOKEN'], sys.argv)
