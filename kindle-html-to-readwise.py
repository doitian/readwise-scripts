#!/usr/bin/env python3

import fileinput
import json

from bs4 import BeautifulSoup

import utils

EN = {}
ZH = {
    "Highlight": "标注",
    " - Location ": " -  位置 ",
    "Note": "笔记",
    " · Location ": " >  位置 ",
}


def _(key):
    return ZH.get(key, key)


def collect_highlights(soup):
    article_template = {
        "title": soup.find(class_="bookTitle").get_text().strip(),
        "author": soup.find(class_="authors").get_text().strip(),
        "source_type": "Kindle",
        "category": "books",
    }
    source_url_dom = soup.find(class_="sourceURL")
    if source_url_dom is not None:
        article_template["source_url"] = source_url_dom.get_text().strip()

    result = []
    last_chapter = None
    for div in soup.select(".bodyContainer > div"):
        if "sectionHeading" in div["class"]:
            article = article_template.copy()
            article["text"] = div.get_text().strip()
            article["note"] = ".h1"
            result.append(article)
        elif "noteHeading" in div["class"] and _("Highlight") in div.get_text():
            article = article_template.copy()
            siblings = div.find_next_siblings("div", limit=3)
            if len(siblings) < 1 or "noteText" not in siblings[0]["class"]:
                raise RuntimeError(f"{div.get_text().strip()} has no noteText")
            article["text"] = siblings[0].get_text().strip()
            heading_parts = div.get_text().strip().split(_(" - Location "))
            if len(heading_parts) == 2:
                article["text"] = f'{article["text"]} (Loc {heading_parts[1]})'
            else:
                heading_parts = div.get_text().strip().split(_(" · Location "))
                if len(heading_parts) == 2:
                    article["text"] = f'{article["text"]} (Loc {heading_parts[1]})'
                    chapter_parts = heading_parts[0].split(") - ", maxsplit=1)
                    if len(chapter_parts) == 2 and chapter_parts[1] != last_chapter:
                        last_chapter = chapter_parts[1]
                        chapter_article = article_template.copy()
                        chapter_article["text"] = chapter_parts[1]
                        chapter_article["note"] = ".h2"
                        result.append(chapter_article)

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
            if len(siblings) > 1 and _("Note") in siblings[1].get_text():
                article["note"] = siblings[2].get_text().strip()

            color_span = div.find("span")
            if (
                color_span is not None
                and "highlight" in " ".join(color_span["class"])
                and color_span.get_text().strip() != "yellow"
                and color_span.get_text().strip() != "黄色"
            ):
                article["note"] = add_tag(
                    article.get("note"), "." + _(color_span.get_text().strip())
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
