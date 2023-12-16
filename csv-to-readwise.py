#!/usr/bin/env python3

import csv
import fileinput
import json
import utils

NAME_MAPPING = {
    "Highlight": "text",
    "Title": "title",
    "Author": "author",
    "URL": "source_url",
    "Note": "note",
    "Location": "location",
    "Date": "highlighted_at",
}


def collect_highlights(lines):
    # Create a CSV reader object
    reader = csv.DictReader(lines)
    fieldnames = reader.fieldnames

    result = []
    for row in reader:
        article = {}
        for field in fieldnames:
            if row[field] != "":
                article[NAME_MAPPING.get(field, field)] = row[field]
        if "location" in article and "location_type" not in article:
            article["location_type"] = "page"
        result.append(article)

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
