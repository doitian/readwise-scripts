import os
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import json
import time


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


def add_tags(highlights, ids, token, user_agent):
    for entry, id in zip(highlights, ids):
        if "note" in entry and entry["note"].startswith("."):
            for tag in entry["note"].splitlines()[0].split():
                req = Request(
                    f"https://readwise.io/api/v2/highlights/{id}/tags/",
                    headers={
                        "Authorization": f"Token {token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "User-Agent": user_agent,
                    },
                    data=json.dumps({"name": tag[1:]}).encode("utf-8"),
                    method="POST",
                )
                urlopen(req)


def create_highlights(highlights, token=None, user_agent=None):
    if token is None:
        token = os.environ["READWISE_TOKEN"]
    if user_agent is None:
        user_agent = os.environ["USER_AGENT"]

    highlights = list(squash_concatenating_highlights(highlights))

    req = Request(
        "https://readwise.io/api/v2/highlights/",
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": user_agent,
        },
        data=json.dumps({"highlights": highlights}).encode("utf-8"),
        method="POST",
    )
    resp = urlopen(req)

    items = json.loads(resp.read().decode("utf-8"))
    if len(items) == 1 and len(items[0]["modified_highlights"]) == len(highlights):
        try:
            add_tags(highlights, items[0]["modified_highlights"], token, user_agent)
        except HTTPError:
            time.sleep(5)
            add_tags(highlights, items[0]["modified_highlights"], token, user_agent)
