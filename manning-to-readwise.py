#!/usr/bin/env python3

import utils
import json
import sys
from bs4 import BeautifulSoup


def parse_authors(authors_html):
    text = authors_html.replace("<br>", ", ").replace("<i>", "").replace("</i>", "")
    text = BeautifulSoup(text, "html.parser").get_text()
    return text.strip()


def deduplicate_highlights(highlights):
    seen = set()
    result = []
    for h in highlights:
        key = (h["color"], h["text"].strip())
        if key not in seen:
            seen.add(key)
            result.append(h)
    return result


def process_manning(input_data):
    product = input_data["product"]
    book_title = product["title"]
    book_author = parse_authors(product["authors"])
    book_url = product["link"]

    chapters = {}
    for item in input_data["scrapbookItems"]:
        chapter_title = item["title"]
        if chapter_title not in chapters:
            chapters[chapter_title] = []
        chapters[chapter_title].append(item)

    result = []

    for chapter_title, items in chapters.items():
        result.append({
            "text": chapter_title,
            "note": ".h1",
        })

        green_texts = []
        other_entries = []

        for item in items:
            notes_text = None
            if "notes" in item and item["notes"]:
                notes_text = item["notes"][0]["text"]
                if notes_text.startswith(".ignore"):
                    continue

            unique_hl = deduplicate_highlights(item.get("highlights", []))

            for hl in unique_hl:
                hl_text = hl["text"].strip()
                if not hl_text:
                    continue

                entry = {
                    "text": hl_text,
                    "highlight_url": item.get("link", ""),
                }
                if notes_text:
                    entry["note"] = notes_text

                if hl["color"] == "green":
                    green_texts.append(hl_text)
                elif notes_text:
                    other_entries.append(entry)
                    notes_text = None
                else:
                    other_entries.append(entry)

        if green_texts:
            merged_text = "\n".join(dict.fromkeys(green_texts))
            merged_entry = {
                "text": merged_text,
                "highlight_url": items[0].get("link", ""),
            }
            result.append(merged_entry)

        seen = set()
        for entry in other_entries:
            if entry["text"] not in seen:
                seen.add(entry["text"])
                result.append(entry)

    base = {
        "title": book_title,
        "author": book_author,
        "source_url": book_url,
        "source_type": "Manning",
        "category": "books",
    }

    for item in result:
        item.update(base)

    return result


def main():
    args = sys.argv[1:]
    dry_run = False
    if args and args[0] == "-n":
        dry_run = True
        args = args[1:]

    if args:
        with open(args[0], encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    highlights = process_manning(data)

    if dry_run:
        print(json.dumps(highlights, indent=2, ensure_ascii=False))
        return

    utils.create_highlights(highlights)


if __name__ == "__main__":
    main()
