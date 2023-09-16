#!/usr/bin/env python3

import utils
import fileinput
import json


# TODO: notes

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
# >> 倾听别人的意见，不断检验自己的做法、想法是否正确，这无论对肉体...
#
# https://weread.qq.com/web/reader/43132e60813ab7439g011388k02e32f0021b02e74f10ece8#1
#
# .h1 第四章曲球
#
# .h2 7
#
# >> 您所说的抵抗，在我看来是令人钦佩的努力。我认为努力不会白费，即使...
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
    pending_text = False
    for line in lines:
        line = line.strip()
        if line == '':
            pending_text = False
            continue

        if line.startswith('《') and line.endswith('》'):
            article['title'] = line[1:-1]
        elif article['author'] is None:
            article['author'] = line
        elif article['source_url'] is None and line.startswith('https://'):
            article['source_url'] = line
        elif line.startswith('.h1 ') or line.startswith('.h2 ') \
                or line.startswith('.h3 ') or line.startswith('◆ '):
            if pending_article is not None:
                result.append(pending_article)
            pending_article = article.copy()
            if line.startswith('◆ '):
                pending_article['text'] = line[1:].lstrip()
                pending_article['note'] = '.h1'
            else:
                pending_article['text'] = line[4:]
                pending_article['note'] = line[:3]
            result.append(pending_article)
            pending_article = None
        elif line.endswith('发表想法'):
            if pending_article is not None:
                result.append(pending_article)
            pending_article = article.copy()
        elif line.startswith('>> '):
            if pending_article is None:
                pending_article = article.copy()
            elif 'text' in pending_article:
                result.append(pending_article)
                pending_article = article.copy()
            pending_text = True
            pending_article['text'] = line[3:]
        elif line.startswith('https://'):
            if pending_article is not None:
                pending_article['highlight_url'] = line
                if line in seen_highlight_urls:
                    raise RuntimeError('duplicated highlight url: ' + line)
                seen_highlight_urls.add(line)
            else:
                raise RuntimeError('expect pending article')
        elif pending_article is not None:
            if pending_text and 'text' in pending_article:
                pending_article['text'] += "\n"
                pending_article['text'] += line
            elif 'note' in pending_article:
                if pending_article['note'] != '':
                    pending_article['note'] += "\n"
                pending_article['note'] += line
            elif 'text' in pending_article:
                pending_article['text'] += "\n"
                pending_article['text'] += line
            else:
                pending_article['note'] = line

    if pending_article is not None:
        result.append(pending_article)
    return result


def main(args):
    dry_run = args[1] == '-n' if len(sys.argv) > 1 else False
    input_args = args[1:] if not dry_run else args[2:]
    highlights = collect_highlights(fileinput.input(input_args))

    if dry_run:
        print(json.dumps(highlights, indent=2, ensure_ascii=False))
        return

    utils.create_highlights(highlights)


if __name__ == '__main__':
    import sys

    main(sys.argv)
