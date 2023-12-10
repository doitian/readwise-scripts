#!/usr/bin/env python3

import utils
import fileinput
import json

def collect_highlights():
    print(soup)
    return []
    article = {
        "title": None,
        "author": None,
        "source_type": "Duku",
        "category": "books",
    }
    result = []
    for line in lines:
        line = line.strip()
        if line == "":
            continue

        if line.startswith("## 《") and line.endswith("》"):
            article["title"] = "读库 - " + line[4:-1]
        elif line.startswith("## "):
            article["title"] = "读库 - " + line[3:]
        elif line.startswith("**"):
            article["author"] = line.split("**")[1].strip()
        elif line.startswith("> "):
            pending_article = article.copy()
            pending_article["text"] = line[2:]
            result.append(pending_article)
        elif line.startswith("# ") or line.startswith("* "):
            pass
        else:
            raise RuntimeError("unexpected line: " + line)

    return result


def main(args):
    dry_run = args[1] == "-n" if len(sys.argv) > 1 else False
    input_args = args[1:] if not dry_run else args[2:]
    soup = BeautifulSoup(''.join(line in fileinput.input(input_args))), 'html.parser')
    print(soup)
    highlights = collect_highlights(soup)

    if dry_run:
        print(json.dumps(highlights, indent=2, ensure_ascii=False))
        return

    utils.create_highlights(highlights)


if __name__ == "__main__":
    import sys

    main(sys.argv)
