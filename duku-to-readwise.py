#!/usr/bin/env python3

import fileinput
import json
from urllib.request import urlopen, Request


# TODO: notes

# Example:
#
# ```
# # 佚名 导出的笔记
#
# * 佚名 通过读库导出的笔记
#
# ## 《地球上最伟大的一场演出》
#
# **8字路口** · **读库** · _2022-09-06 13:56_
#
# > 1985年7月在英美举办的Live Aid演唱会，是一场将摇滚乐与生命意义真正结合在一起的活动。
#
# > 彼时年少的我们沐浴着大师们的光辉，生长出“纵横四海，改造国家”的理想。
def collect_highlights(lines):
    article = {
        'title': None,
        'author': None,
        'source_type': 'Duku',
        'category': 'books'
    }
    result = []
    for line in lines:
        line = line.strip()
        if line == '':
            continue

        if line.startswith('## 《') and line.endswith('》'):
            article['title'] = '读库 - ' + line[4:-1]
        elif line.startswith('## '):
            article['title'] = '读库 - ' + line[3:]
        elif line.startswith('**'):
            article['author'] = line.split('**')[1].strip()
        elif line.startswith('> '):
            pending_article = article.copy()
            pending_article['text'] = line[2:]
            result.append(pending_article)
        elif line.startswith('# ') or line.startswith('* '):
            pass
        else:
            raise RuntimeError('unexpected line: ' + line)

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
