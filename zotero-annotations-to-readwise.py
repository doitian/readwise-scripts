#!/usr/bin/env python3

# ruff: noqa: E501

import shutil
import utils
from titlecase import titlecase
import json
import urllib.parse
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime

UPLOADS_SITE = "https://blog.iany.me"
ZOTERO_STORAGE_DIR = Path.home() / "Zotero" / "storage"
UPLOADS_DIR = Path("uploads") / datetime.now().strftime("%Y%m") / "zotero"


def get_image_path(attachment_key):
    dir = ZOTERO_STORAGE_DIR / attachment_key
    for ext in ["jpg", "jpeg", "png", "gif", "webp"]:
        try_path = dir / f"image.{ext}"
        if try_path.exists():
            return try_path


def copy_image(attachment_key):
    image_path = get_image_path(attachment_key)
    if image_path:
        # copy the image directory into UPLOADS_DIR
        shutil.copytree(image_path.parent, UPLOADS_DIR / image_path.parent.name, dirs_exist_ok=True)


def get_items():
    with urlopen(
        "http://127.0.0.1:23119/better-bibtex/cayw?selected=1&format=translate&translator=csljson"
    ) as resp:
        return json.loads(resp.read().decode("utf-8"))


def format_author(authors):
    return " & ".join(
        a["literal"] if "literal" in a else f"{a['given']} {a['family']}"
        for a in authors
    )


def collect_highlights(item, highlights):
    article = {
        "title": titlecase(item["title"]),
        "author": format_author(item["author"]),
        "source_url": f"zotero://select/library/items/{item['item-key']}",
        "source_type": "Zotero",
        "category": "books" if item["type"] == "book" else "articles",
    }

    req = Request(
        "http://localhost:23119/better-bibtex/json-rpc",
        data=json.dumps(
            {"jsonrpc": "2.0", "method": "item.notes", "params": [[item["id"]]]}
        ).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urlopen(req) as resp:
        notes = json.loads(resp.read().decode("utf-8"))["result"][item["id"]]

    for note in notes:
        soup = BeautifulSoup(replace_br(note), "html.parser")
        if soup.div is None:
            continue
        h1 = soup.find("h1")
        if not (h1 and h1.get_text().startswith("Annotation")):
            continue
        for p in soup.find_all("p"):
            highlight_tags = []
            for tag in p.select("span.highlight"):
                highlight_tags.append(tag.extract())
            for tag in p.select("span.underline"):
                highlight_tags.append(tag.extract())
            for tag in p.select("img.data-annotation"):
                highlight_tags.append(tag.extract())
            for tag in p.select("span.citation"):
                tag.decompose()
            annotation = bs2md(p).strip()
            highlights.append(
                format_highlight(article.copy(), highlight_tags, annotation)
            )


def get_highlight_text(highlight):
    text = bs2md(BeautifulSoup(replace_br(highlight), "html.parser")).strip()
    if text.startswith("“") and text.endswith("”"):
        return text[1:-1]
    if text.startswith("\u201c") and text.endswith("\u201d"):
        return text[1:-1]
    return text


def replace_br(html):
    return str(html).replace("<br/>", "\n").replace("<br>", "\n")


def bs2md(bs):
    from bs4 import NavigableString

    if bs is None:
        return ""

    # If it's a text node (NavigableString), return the text
    if isinstance(bs, NavigableString):
        return str(bs)

    # If it's a Tag, process it
    if hasattr(bs, "name"):
        inner = "".join(bs2md(child) for child in bs.children)
        if bs.name in ["b", "strong"]:
            return f"**{inner}**"
        elif bs.name in ["i", "em", "emph"]:
            return f"*{inner}*"
        elif bs.name == "code":
            return f"`{inner}`"
        elif bs.name == "img":
            attachment_key = bs.get("data-attachment-key")
            image_path = get_image_path(attachment_key)
            if image_path is None:
                raise RuntimeError(f"Image not found: {attachment_key}")

            copy_image(attachment_key)
            return f"![{attachment_key}]({UPLOADS_SITE}/{UPLOADS_DIR.as_posix()}/{attachment_key}/{image_path.name})"
        else:
            return inner

    # Fallback for other types
    return bs.get_text()


def format_highlight(entry, highlight_tags, annotation):
    if len(highlight_tags) == 0:
        entry["text"] = annotation
        return entry

    entry["text"] = "…".join(get_highlight_text(h) for h in highlight_tags)

    if annotation != "":
        if annotation.startswith(".") and "\n" not in annotation:
            entry["note"] = annotation + "\n"
        else:
            entry["note"] = annotation
    data = json.loads(urllib.parse.unquote(highlight_tags[0]["data-annotation"]))
    is_epub = data["position"].get("type", "") == "FragmentSelector"
    item_key = data["attachmentURI"].split("/")[-1]
    if not is_epub:
        entry["location_type"] = "page"
        entry["location"] = int(data["pageLabel"])
        entry["highlight_url"] = (
            f"zotero://open-pdf/library/items/{item_key}?page={data['position']['pageIndex']}&annotation={data['annotationKey']}"
        )
    else:
        entry["highlight_url"] = (
            f"zotero://open-pdf/library/items/{item_key}?annotation={data['annotationKey']}"
        )

    return entry


def is_title(entry):
    return (
        "note" in entry
        and entry["note"] != ""
        and entry["note"].split()[0] in [".h1", ".h2", ".h3"]
    )


def is_concatenating(entry):
    return (
        "note" in entry
        and entry["note"] != ""
        and entry["note"].split()[0] in [".c1", ".c2", ".c3", ".c4", ".c5"]
    )


def concatenate_highlights(highlights):
    result = highlights[0]
    result["text"] = " ".join(entry["text"] for entry in highlights)
    notes = []
    for entry in highlights:
        entry_note = entry["note"][3:].strip()
        if entry_note != "":
            notes.append(entry_note)
    if len(notes) > 0:
        result["note"] = "\n".join(notes)
    else:
        del result["note"]

    return result


def squash_concatenating_highlights(highlights):
    pending_spans = []
    for entry in highlights:
        if is_concatenating(entry):
            if entry["note"].split()[0] == ".c1":
                if len(pending_spans) > 0:
                    yield concatenate_highlights(pending_spans)
                pending_spans = [entry]
            else:
                pending_spans.append(entry)
        else:
            if len(pending_spans) > 0:
                yield concatenate_highlights(pending_spans)
                pending_spans = []
            yield entry

    if len(pending_spans) > 0:
        yield concatenate_highlights(pending_spans)


def main(dry_run=False):
    items = get_items()
    highlights = []
    for item in items:
        collect_highlights(item, highlights)

    highlights = list(squash_concatenating_highlights(highlights))

    if dry_run:
        print(json.dumps(highlights, indent=2))
        return

    utils.create_highlights(highlights)


if __name__ == "__main__":
    import sys

    dry_run = sys.argv[1] == "-n" if len(sys.argv) > 1 else False
    main(dry_run)
