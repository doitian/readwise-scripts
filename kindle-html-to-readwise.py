#!/usr/bin/env python3

import fileinput
import json
import os

from bs4 import BeautifulSoup

import utils


def collect_highlights(soup):
    article_template = {
        "title": soup.find(class_="bookTitle").get_text().strip(),
        "author": soup.find(class_="authors").get_text().strip(),
        "source_type": "Kindle",
        "category": "books",
    }
    if "SOURCE_URL" in os.environ:
        article_template["source_url"] = os.environ["SOURCE_URL"]

    result = []
    for div in soup.select(".bodyContainer > div"):
        if "sectionHeading" in div["class"]:
            article = article_template.copy()
            article["text"] = div.get_text().strip()
            article["note"] = ".h1"
            result.append(article)
        elif "noteHeading" in div["class"] and "Highlight" in div.get_text():
            article = article_template.copy()
            siblings = div.find_next_siblings("div", limit=3)
            if len(siblings) < 1 or "noteText" not in siblings[0]["class"]:
                raise RuntimeError(f"{div.get_text().strip()} has no noteText")
            article["text"] = siblings[0].get_text().strip()
            heading_parts = div.get_text().strip().split(" - Location ")
            if len(heading_parts) == 2:
                article["text"] = f'{article["text"]} (Loc {heading_parts[1]})'
            else:
                heading_parts = div.get_text().strip().split(" · Location ")
                if len(heading_parts) == 2:
                    article["text"] = f'{article["text"]} (Loc {heading_parts[1]})'

            result.append(article)
            if len(siblings) == 2:
                raise RuntimeError(
                    f"{div.get_text().strip()} has odd number of following siblings"
                )
            if (
                len(siblings) == 3
                and "sectionHeading" not in siblings[1]["class"]
                and (
                    "noteHeading" not in siblings[1]["class"]
                    or "noteText" not in siblings[2]["class"]
                )
            ):
                raise RuntimeError(
                    f"{div.get_text().strip()} has unknown following siblings"
                )
            if len(siblings) > 1 and "Note" in siblings[1].get_text():
                article["note"] = siblings[2].get_text().strip()

            color_span = div.find("span")
            if (
                color_span is not None
                and "highlight" in " ".join(color_span["class"])
                and color_span.get_text().strip() != "yellow"
            ):
                article["note"] = add_tag(
                    article.get("note"), "." + color_span.get_text().strip()
                )

    return result


def add_tag(note, tag):
    if note is None:
        return tag
    if note.startswith("."):
        return " ".join([tag, note])
    else:
        return "\n\n".join(tag, note)


def main(args):
    dry_run = args[1] == "-n" if len(sys.argv) > 1 else False
    input_args = args[1:] if not dry_run else args[2:]
    soup = BeautifulSoup(
        "".join(line for line in fileinput.input(input_args)), "html.parser"
    )
    highlights = collect_highlights(soup)

    if dry_run:
        print(json.dumps(highlights, indent=2, ensure_ascii=False))
        return

    utils.create_highlights(highlights)


if __name__ == "__main__":
    import sys

    main(sys.argv)
