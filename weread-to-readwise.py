#!/usr/bin/env python3

import utils
import fileinput
import json


def finalize_article(result, article):
    if article is not None:
        article["text"] = article["text"].strip()
        if "note" in article:
            article["note"] = article["note"].strip()

        if len(result) > 0 and result[-1]["text"] == article["text"]:
            result[-1] = article
        else:
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
    state = "head"
    for line in lines:
        line = line.strip()
        if (
            line.startswith("◆ ")
            or line.startswith(".h1 ")
            or line.startswith(".h2 ")
            or line.startswith(".h3 ")
        ):
            state = "body"

        if state == "head":
            if line.startswith("《") and line.endswith("》"):
                article["title"] = line[1:-1]
            elif article["author"] is None:
                article["author"] = line
            elif article["source_url"] is None and (
                line.startswith("https://") or line.startswith("<https://")
            ):
                article["source_url"] = (
                    line if line.startswith("https://") else line[1:-1]
                )
            elif line == "":
                state = "body"

        elif state == "body":
            if line.startswith("◆ "):
                if line.endswith("发表想法"):
                    finalize_article(result, pending_article)
                    pending_article = article.copy()
                    pending_article["text"] = ""
                    pending_article["note"] = ""
                    state = "note"
                else:
                    state = "highlight"
                    finalize_article(result, pending_article)
                    pending_article = article.copy()
                    pending_article["text"] = line[1:].lstrip()
            elif line != "":
                finalize_article(result, pending_article)
                pending_article = article.copy()
                if (
                    line.startswith(".h1 ")
                    or line.startswith(".h2 ")
                    or line.startswith(".h3 ")
                ):
                    pending_article["text"] = line[4:]
                    pending_article["note"] = line[:3]
                else:
                    pending_article["text"] = line
                    pending_article["note"] = ".h1"
                finalize_article(result, pending_article)
                pending_article = None

        elif state == "note":
            if line.startswith("原文："):
                pending_article["text"] = line[3:]
                state = "highlight"
            else:
                pending_article["note"] = pending_article["note"] + "\n" + line

        elif state == "highlight":
            if line == "":
                state = "highlight-ending"
            else:
                pending_article["text"] = pending_article["text"] + "\n" + line
        elif state == "highlight-ending":
            if line == "" or line == "-- 来自微信读书":
                finalize_article(result, pending_article)
                pending_article = None
                state = "body"
            else:
                pending_article["text"] = "\n" + pending_article["text"] + "\n" + line
                state = "highlight"

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
