#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import re
from collections import OrderedDict


def sanitize_author(author):
    if not author:
        return ""
    author = author.replace("_", " ")
    author = author.replace(":", "").replace("?", "").replace('"', "")
    author = author.replace("/", "").replace("|", "").replace("*", "")
    author = author.replace("<", "").replace(">", "").replace("#", " ")
    return author.strip()


def format_author_for_title(author):
    if not author:
        return ""
    author = sanitize_author(author)
    first_author = author.split(" & ")[0].split(", ")[0]
    if " & " in author or ", " in author:
        return f"{first_author} et al."
    return first_author


def sanitize_filename(name):
    if not name:
        return "untitled"
    name = name.replace("#", " ")
    name = re.sub(r'[\\/:*?"<>|]', "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name or "untitled"


def process_note(note_text):
    if not note_text:
        return [], None, None, None
    lines = note_text.splitlines()
    first_line = lines[0].strip()
    if not first_line.startswith("."):
        return [], None, None, note_text

    tags_line = first_line
    raw_tags = [tag for tag in tags_line.split() if tag.startswith(".")]
    tags = [tag.lstrip(".") for tag in raw_tags]

    heading_level = None
    concat_index = None
    remaining_tags = []
    for tag in tags:
        if re.fullmatch(r"h[1-3]", tag):
            if heading_level is None:
                heading_level = int(tag[1])
            continue
        if re.fullmatch(r"c[1-9]", tag):
            if concat_index is None:
                concat_index = int(tag[1])
            continue
        remaining_tags.append(tag)

    note_content = "\n".join(lines[1:]).strip()
    return remaining_tags, heading_level, concat_index, note_content


def build_highlight_id(text, location, title):
    raw = f"{text}|{location}|{title}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]


def normalize_text(text):
    return text.replace("␣", " ")


def normalize_note(note):
    return note.replace("\n∎", "\n").replace("␣", " ").strip()


def split_highlight_text(text):
    text = normalize_text(text)
    if "↩︎" in text:
        first, rest = text.split("↩︎", 1)
        if text.startswith("↩︎"):
            first_part = "↩︎"
            rest_part = rest.strip()
        else:
            first_part = first.rstrip()
            rest_part = rest.strip()
        return first_part, rest_part
    return text, None


def merge_consecutive_highlights(highlights):
    merged = []
    i = 0
    while i < len(highlights):
        current = highlights[i]
        if current.get("concat_index") == 1:
            group = [current]
            expected = 2
            j = i + 1
            while j < len(highlights):
                next_item = highlights[j]
                if next_item.get("concat_index") == expected:
                    group.append(next_item)
                    expected += 1
                    j += 1
                else:
                    break
            if len(group) > 1:
                merged.append(concatenate_group(group))
                i = j
                continue
        merged.append(current)
        i += 1
    return merged


def concatenate_group(group):
    base = dict(group[0])
    base["text"] = " ".join(item.get("text", "").strip() for item in group).strip()

    combined_tags = []
    seen_tags = set()
    for item in group:
        for tag in item.get("tags", []):
            if tag not in seen_tags:
                combined_tags.append(tag)
                seen_tags.add(tag)
    base["tags"] = combined_tags

    notes = []
    for item in group:
        note_content = item.get("note_content") or ""
        note_content = note_content.strip()
        if note_content:
            notes.append(note_content)
    base["note_content"] = "\n".join(notes).strip() if notes else None

    base["concat_index"] = None
    base["heading_level"] = None
    return base


def format_location(highlight):
    location = highlight.get("location")
    if not location:
        return None
    location_type = highlight.get("location_type")
    if location_type:
        return f"{location_type} {location}"
    return str(location)


def format_highlight_markdown(highlight):
    text = highlight.get("text") or ""
    note_content = highlight.get("note_content")
    tags = highlight.get("tags") or []
    heading_level = highlight.get("heading_level")

    if heading_level:
        heading_text = normalize_text(text).strip()
        if not heading_text and note_content:
            heading_text = normalize_note(note_content)
            note_content = None
        if not heading_text:
            return ""
        lines = [f"{'#' * heading_level} {heading_text}"]
        if note_content:
            lines.append("")
            lines.append(normalize_note(note_content))
        return "\n".join(lines)

    if len(text.strip()) <= 1 and note_content:
        return normalize_note(note_content)

    first_part, rest_part = split_highlight_text(text)
    first_part = first_part.strip()
    if not first_part:
        first_part = normalize_text(text).strip()

    location_text = format_location(highlight)
    location_url = highlight.get("highlight_url")
    if location_text and location_url:
        location_suffix = f" ([{location_text}]({location_url}))"
    elif location_text:
        location_suffix = f" ({location_text})"
    else:
        location_suffix = ""

    anchor_override = None
    note_body = note_content
    if note_content:
        note_lines = note_content.splitlines()
        if note_lines and note_lines[0].strip().startswith("^"):
            anchor_override = note_lines[0].strip()
            note_body = "\n".join(note_lines[1:]).strip()

    highlight_id = build_highlight_id(text, location_text or "", highlight.get("title", ""))
    anchor_text = anchor_override or f"^{highlight_id}"

    lines = [f"- {first_part}{location_suffix} {anchor_text}".rstrip()]

    if rest_part:
        lines.append(f"    {rest_part}")

    if tags:
        lines.append("")
        lines.append("    " + " ".join(f"#{tag}" for tag in tags))

    note_body = normalize_note(note_body) if note_body else ""
    if note_body:
        lines.append(f"    {note_body}")

    return "\n".join(lines)


def build_page_title(author, title):
    author_part = format_author_for_title(author)
    if author_part:
        return f"# {author_part} - {title} (Highlights)"
    return f"# {title} (Highlights)"


def build_metadata_section(entry):
    lines = ["## Metadata"]
    source_type = entry.get("source_type") or "readwise"
    lines.append(f"**Source**:: #from/{source_type.lower().replace(' ', '-')}")
    if entry.get("author"):
        authors = sanitize_author(entry["author"])
        authors = authors.replace(", ", "]], [[").replace(" & ", "]], [[")
        lines.append(f"**Authors**:: [[{authors}]]")
    if entry.get("title"):
        lines.append(f"**Full Title**:: {entry['title']}")
    if entry.get("category"):
        lines.append(f"**Category**:: #{entry['category']} #readwise/{entry['category']}")
    if entry.get("source_url"):
        source_url = str(entry["source_url"]).strip()
        if source_url.lower().startswith("zotero://"):
            lines.append(
                f"**Zotero App Link**:: [Open in Zotero]({source_url})"
            )
        else:
            print(source_url)
            print(source_url.lower().startswith("weread://"))
            lines.append(f"**URL**:: {source_url}")
    return "\n".join(lines)


def build_filename(entry):
    author_part = format_author_for_title(entry.get("author"))
    title = entry.get("title") or "Untitled"
    if author_part:
        base = f"{author_part} - {title} (Highlights)"
    else:
        base = f"{title} (Highlights)"
    return sanitize_filename(base) + ".md"


def group_highlights(entries):
    groups = OrderedDict()
    for entry in entries:
        key = (entry.get("source_url"), entry.get("title"), entry.get("author"))
        if key not in groups:
            groups[key] = []
        groups[key].append(entry)
    return groups


def parse_entries(raw_entries):
    processed = []
    for entry in raw_entries:
        tags, heading_level, concat_index, note_content = process_note(entry.get("note"))
        processed.append(
            {
                **entry,
                "tags": tags,
                "heading_level": heading_level,
                "concat_index": concat_index,
                "note_content": note_content,
            }
        )
    return processed


def build_markdown_for_group(entries):
    if not entries:
        return ""
    first = entries[0]
    lines = [
        build_page_title(first.get("author"), first.get("title")),
        "",
        build_metadata_section(first),
        "",
        "## Highlights",
    ]

    merged_entries = merge_consecutive_highlights(entries)
    for entry in merged_entries:
        highlight_markdown = format_highlight_markdown(entry)
        if highlight_markdown:
            lines.append(highlight_markdown)
    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="Convert Readwise JSON to Markdown.")
    parser.add_argument("input_json", help="Path to Readwise JSON export")
    parser.add_argument(
        "-o",
        "--output-dir",
        default=".",
        help="Output directory for Markdown files",
    )
    args = parser.parse_args()

    with open(args.input_json, "r", encoding="utf-8") as handle:
        raw_entries = json.load(handle)

    processed_entries = parse_entries(raw_entries)
    grouped = group_highlights(processed_entries)

    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    for _, entries in grouped.items():
        markdown = build_markdown_for_group(entries)
        if not markdown:
            continue
        filename = build_filename(entries[0])
        output_path = os.path.join(output_dir, filename)
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(markdown)


if __name__ == "__main__":
    main()
