#!/usr/bin/env python3
"""
Alphabetically sort recipes in the Recipes Google Doc.

Each recipe is one block: title line (+ any following Note lines).
Blocks are sorted case-insensitively by title only.
No blank lines are inserted between recipes (single newlines only).

The service account often has viewer+copy access but not edit on the
live Doc. In that case this script writes a sorted copy and shares it
with the Doc owner.
"""

from __future__ import annotations

import argparse
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import creds
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

DEFAULT_DOC_ID = "1ZKRBHoqKoQQ7RcnHoNtLtx0O0ae7ZMHF_XF1UUNp2kY"
SHARE_WITH = "dustinlwicker@gmail.com"


def _run_link(text_run: Dict[str, Any]) -> Optional[str]:
    if "link" in text_run and "url" in text_run["link"]:
        return text_run["link"]["url"]
    style = text_run.get("textStyle") or {}
    if "link" in style and "url" in style["link"]:
        return style["link"]["url"]
    return None


def _is_note(text: str) -> bool:
    return text.strip().lower().startswith("note")


def extract_title(runs: List[Dict[str, Any]], full_text: str) -> str:
    """Match recipe_parser title rules: text before first link, cleaned."""
    title_parts: List[str] = []
    for run in runs:
        content = run["text"].strip()
        if run.get("url"):
            break
        if content:
            title_parts.append(content)

    title = " ".join(title_parts).strip()
    if not title:
        title = full_text.strip()

    title_lower = title.lower()
    if " recipe" in title_lower:
        title = title[: title_lower.index(" recipe")].strip()
    elif " quick_recipe" in title_lower or " quick recipe" in title_lower:
        title = title[: title_lower.index(" quick")].strip()

    words = title.split()
    cleaned = [
        w for w in words if not re.match(r"^[A-Za-z]+_(recipe|picture)$", w, re.I)
    ]
    title = " ".join(cleaned).strip()
    title = re.sub(r"\s+-\s*$", "", title)
    title = re.sub(r"-\s*$", "", title)
    return title.strip()


def fetch_paragraphs(docs, doc_id: str) -> Tuple[List[Dict[str, Any]], int]:
    doc = docs.documents().get(documentId=doc_id).execute()
    content = doc.get("body", {}).get("content", [])
    end_index = content[-1]["endIndex"]
    paras: List[Dict[str, Any]] = []

    for element in content:
        if "paragraph" not in element:
            continue
        runs = []
        text = ""
        for elem in element["paragraph"].get("elements", []):
            if "textRun" not in elem:
                continue
            tr = elem["textRun"]
            t = tr.get("content", "")
            style = tr.get("textStyle") or {}
            runs.append(
                {
                    "text": t,
                    "url": _run_link(tr),
                    "bold": style.get("bold"),
                    "italic": style.get("italic"),
                    "underline": style.get("underline"),
                }
            )
            text += t
        paras.append({"text": text, "runs": runs})
    return paras, end_index


def build_blocks(paras: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    i = 0
    while i < len(paras):
        text = paras[i]["text"]
        if not text.strip():
            i += 1
            continue
        if _is_note(text):
            if blocks:
                blocks[-1]["paras"].append(paras[i])
            else:
                blocks.append(
                    {
                        "title": text.strip(),
                        "paras": [paras[i]],
                    }
                )
            i += 1
            continue

        block = {
            "title": extract_title(paras[i]["runs"], text),
            "paras": [paras[i]],
        }
        j = i + 1
        while j < len(paras):
            nt = paras[j]["text"]
            if not nt.strip():
                j += 1
                continue
            if _is_note(nt):
                block["paras"].append(paras[j])
                j += 1
                continue
            break
        blocks.append(block)
        i = j
    return blocks


def compose_sorted_content(
    blocks: List[Dict[str, Any]],
) -> Tuple[str, List[Dict[str, Any]]]:
    """Return full document text and link style ranges (absolute indices)."""
    pieces: List[str] = []
    links: List[Dict[str, Any]] = []
    cursor = 1  # Docs body content starts at index 1

    for bi, block in enumerate(blocks):
        for pi, para in enumerate(block["paras"]):
            runs = para["runs"]
            # Drop trailing newline from last run; we add exactly one \n per para
            normalized = []
            for run in runs:
                t = run["text"]
                normalized.append({**run, "text": t})
            if normalized and normalized[-1]["text"].endswith("\n"):
                normalized[-1]["text"] = normalized[-1]["text"][:-1]
            # Join run texts; ensure paragraph ends with single newline
            for run in normalized:
                t = run["text"]
                if not t:
                    continue
                start = cursor
                pieces.append(t)
                cursor += len(t)
                if run.get("url"):
                    links.append(
                        {
                            "start": start,
                            "end": cursor,
                            "url": run["url"],
                            "bold": run.get("bold"),
                            "italic": run.get("italic"),
                            "underline": run.get("underline"),
                        }
                    )
            pieces.append("\n")
            cursor += 1

    return "".join(pieces), links


def rewrite_document(docs, doc_id: str, text: str, links: List[Dict[str, Any]]) -> None:
    doc = docs.documents().get(documentId=doc_id).execute()
    end_index = doc["body"]["content"][-1]["endIndex"]

    requests: List[Dict[str, Any]] = []
    if end_index > 2:
        requests.append(
            {
                "deleteContentRange": {
                    "range": {"startIndex": 1, "endIndex": end_index - 1}
                }
            }
        )
    requests.append({"insertText": {"location": {"index": 1}, "text": text}})

    for link in links:
        style: Dict[str, Any] = {"link": {"url": link["url"]}}
        fields = ["link"]
        if link.get("underline") is not None:
            style["underline"] = link["underline"]
            fields.append("underline")
        if link.get("bold") is not None:
            style["bold"] = link["bold"]
            fields.append("bold")
        if link.get("italic") is not None:
            style["italic"] = link["italic"]
            fields.append("italic")
        # Docs links are typically blue + underlined
        if "underline" not in fields:
            style["underline"] = True
            fields.append("underline")
        requests.append(
            {
                "updateTextStyle": {
                    "range": {"startIndex": link["start"], "endIndex": link["end"]},
                    "textStyle": style,
                    "fields": ",".join(fields),
                }
            }
        )

    # Batch in chunks to stay under request limits
    chunk_size = 100
    for i in range(0, len(requests), chunk_size):
        docs.documents().batchUpdate(
            documentId=doc_id, body={"requests": requests[i : i + chunk_size]}
        ).execute()


def can_edit(drive, file_id: str) -> bool:
    meta = (
        drive.files()
        .get(
            fileId=file_id,
            fields="capabilities/canEdit,capabilities/canModifyContent",
            supportsAllDrives=True,
        )
        .execute()
    )
    caps = meta.get("capabilities", {})
    return bool(caps.get("canEdit") and caps.get("canModifyContent"))


def copy_file(drive, file_id: str, name: str) -> Dict[str, Any]:
    return (
        drive.files()
        .copy(
            fileId=file_id,
            body={"name": name},
            fields="id,name,webViewLink",
            supportsAllDrives=True,
        )
        .execute()
    )


def share_with_user(drive, file_id: str, email: str, role: str = "writer") -> None:
    try:
        drive.permissions().create(
            fileId=file_id,
            body={"type": "user", "role": role, "emailAddress": email},
            sendNotificationEmail=False,
            supportsAllDrives=True,
            fields="id",
        ).execute()
    except HttpError as e:
        # Already shared is fine
        if e.resp.status not in (400, 403, 409):
            raise


def file_url(file_id: str) -> str:
    return f"https://docs.google.com/document/d/{file_id}/edit"


def main() -> None:
    parser = argparse.ArgumentParser(description="Sort Recipes Google Doc A–Z by title")
    parser.add_argument("--doc-id", default=DEFAULT_DOC_ID)
    parser.add_argument(
        "--share-with",
        default=os.environ.get("RECIPES_SHARE_WITH", SHARE_WITH),
        help="Email to grant writer on backup/sorted copies",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print sort order only; no Drive writes",
    )
    args = parser.parse_args()

    credentials = creds.login()
    docs = build("docs", "v1", credentials=credentials)
    drive = build("drive", "v3", credentials=credentials)

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    paras, _ = fetch_paragraphs(docs, args.doc_id)
    blocks = build_blocks(paras)
    sorted_blocks = sorted(blocks, key=lambda b: b["title"].casefold())

    print(f"Parsed {len(blocks)} recipe blocks from {args.doc_id}")
    print("First 10 after sort:")
    for b in sorted_blocks[:10]:
        note_n = len(b["paras"]) - 1
        extra = f" (+{note_n} note)" if note_n else ""
        print(f"  - {b['title']}{extra}")
    print("...")
    print("Last 5 after sort:")
    for b in sorted_blocks[-5:]:
        print(f"  - {b['title']}")

    if args.dry_run:
        print("Dry run — no changes written.")
        return

    # 1) Backup of current (unsorted) state
    backup = copy_file(
        drive, args.doc_id, f"Recipes - backup {stamp} before A-Z sort"
    )
    share_with_user(drive, backup["id"], args.share_with)
    print(f"Backup: {file_url(backup['id'])}")

    text, links = compose_sorted_content(sorted_blocks)
    link_count = len(links)
    print(f"Composed {len(text)} chars, {link_count} hyperlink runs")

    # 2) Prefer rewriting the live Doc; otherwise write a sorted copy
    target_id = args.doc_id
    wrote_copy = False
    if not can_edit(drive, args.doc_id):
        sorted_copy = copy_file(
            drive, args.doc_id, f"Recipes - A-Z sorted {stamp}"
        )
        share_with_user(drive, sorted_copy["id"], args.share_with)
        target_id = sorted_copy["id"]
        wrote_copy = True
        print(
            "Service account cannot edit the live Doc; "
            f"writing sorted copy instead: {file_url(target_id)}"
        )

    rewrite_document(docs, target_id, text, links)
    print(f"Sorted document ready: {file_url(target_id)}")
    if wrote_copy:
        print(
            "To replace the live Doc in place, grant Editor access on the original "
            f"to the service account, then re-run this script.\n"
            f"  SA: check GOOGLE_SERVICE_ACCOUNT client_email"
        )


if __name__ == "__main__":
    main()
