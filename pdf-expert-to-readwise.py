#!/usr/bin/env python3

import utils
import fileinput
import json


def finalize_article(result, article):
    if article is not None:
        article["text"] = article["text"].strip()
        if "note" in article:
            article["note"] = article["note"].strip()

        result.append(article)


def collect_highlights(lines):
    article = {
        "title": None,
        "author": None,
        "source_url": None,
        "source_type": "Weread",
        "category": "books",
    }
    result = []
    pending_article = None
    state = "body"
    lineno = 0
    for line in lines:
        lineno += 1
        line = line.strip()

        if lineno == 1:
            author, title = line[len("# Annotation Summary of ") :].split(
                " - ", maxsplit=1
            )
            title = title.rsplit(".pdf", maxsplit=1)[0]

            article["author"] = author
            article["title"] = title
        elif lineno == 2 and line.startswith("<"):
            article["source_url"] = line.strip()[1:-1]
        elif line.startswith("#### "):
            state = "body"

            finalize_article(result, pending_article)
            pending_article = article.copy()
            pending_article["text"] = line[5:]
            pending_article["note"] = ".h1"
            finalize_article(result, pending_article)
            pending_article = None
        elif line.startswith("*Highlight ["):
            state = "highlight"

            finalize_article(result, pending_article)
            pending_article = article.copy()

            page = line.split(" [")[1].split("]")[0]
            text = line.split("]:* ", maxsplit=1)[1]
            pending_article["text"] = f"{text} (Page {page})"
        elif line.startswith("*and Note ["):
            state = "note"

            text = line.split("]:* ", maxsplit=1)[1]
            pending_article["note"] = text
            if text == ".h1" or text == ".h2" or text == ".h3":
                pending_article["text"] = pending_article["text"].rsplit(
                    " (Page", maxsplit=1
                )[0]
        elif state == "highlight":
            pending_article["text"] = pending_article["text"] + "\n" + line.rstrip()
        elif state == "note":
            pending_article["note"] = pending_article["note"] + "\n" + line.rstrip()

    finalize_article(result, pending_article)
    return result


def main(args):
    dry_run = args[1] == "-n" if len(sys.argv) > 1 else False
    input_args = args[1:] if not dry_run else args[2:]
    highlights = collect_highlights(fileinput.input(input_args))

    if dry_run:
        print(json.dumps(highlights, indent=2, ensure_ascii=False))
        return

    utils.create_highlights(highlights)


if __name__ == "__main__":
    import sys

    main(sys.argv)
