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
        key = h["text"].strip()
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

    def flush_pending(pending_green, pending_notes_list, pending_url):
        if not pending_green:
            return
        merged_text = "\n".join(dict.fromkeys(pending_green))
        merged_entry = {
            "text": merged_text,
            "highlight_url": pending_url,
        }
        if pending_notes_list:
            merged_entry["note"] = "\n\n".join(dict.fromkeys(pending_notes_list))
        result.append(merged_entry)

    for chapter_title, items in chapters.items():
        result.append(
            {
                "text": chapter_title,
                "note": ".h1",
            }
        )

        pending_green = []
        pending_notes_list = []
        pending_url = ""
        items_to_merge = 0

        for item in items:
            notes_text = None
            if "notes" in item and item["notes"]:
                notes_text = "\n\n".join(
                    n["text"] for n in item["notes"] if n.get("text")
                )
                if notes_text.startswith(".ignore"):
                    flush_pending(pending_green, pending_notes_list, pending_url)
                    pending_green = []
                    pending_notes_list = []
                    items_to_merge = 0
                    continue
            unique_hl = deduplicate_highlights(item.get("highlights", []))

            green_count = sum(
                1 for h in item.get("highlights", []) if h["color"] == "green"
            )
            item_green_texts = []

            for hl in unique_hl:
                hl_text = hl["text"].strip()
                if not hl_text:
                    continue

                if hl["color"] == "gray":
                    continue

                if hl["color"] == "green":
                    item_green_texts.append(hl_text)
                else:
                    flush_pending(pending_green, pending_notes_list, pending_url)
                    pending_green = []
                    pending_notes_list = []
                    items_to_merge = 0

                    entry = {
                        "text": hl_text,
                        "highlight_url": item.get("link", ""),
                    }
                    if notes_text:
                        entry["note"] = notes_text
                    result.append(entry)

            if item_green_texts:
                pending_green.extend(item_green_texts)
                if notes_text and notes_text.strip():
                    pending_notes_list.append(notes_text)
                pending_url = item.get("link", "")

                if items_to_merge == 0 and green_count > 0:
                    items_to_merge = green_count
                if items_to_merge > 0:
                    items_to_merge -= 1
                    if items_to_merge == 0:
                        flush_pending(pending_green, pending_notes_list, pending_url)
                        pending_green = []
                        pending_notes_list = []

        flush_pending(pending_green, pending_notes_list, pending_url)

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
