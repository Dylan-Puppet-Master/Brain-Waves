"""Comments, as Google Drive holds them for a spreadsheet.

Using Drive's own comments rather than a tab of our own is what lets a village leader
discuss a card in the Google Sheets sidebar and a Brain Waves user see the same thread,
each of them writing as themselves and each of them getting the usual Google notification.

This module is the transport. `brainwaves.comments` decides which card a thread is about.
"""

import json
from dataclasses import dataclass
from datetime import datetime

from brainwaves.google.retry import retrying

COMMENT_FIELDS = (
    "id,content,resolved,anchor,createdTime,author/displayName,"
    "replies(id,content,createdTime,author/displayName)"
)
FIELDS = f"comments({COMMENT_FIELDS}),nextPageToken"
PAGE_SIZE = 100


@dataclass(frozen=True)
class RawReply:
    """One reply, straight from Drive."""

    id: str
    author: str
    created: datetime
    text: str


@dataclass(frozen=True)
class RawComment:
    """One thread, straight from Drive, before it is matched to a card."""

    id: str
    author: str
    created: datetime
    text: str
    resolved: bool
    anchor: str
    replies: tuple[RawReply, ...]


class CommentStore:
    """Read and write the comments on one spreadsheet."""

    def __init__(self, credentials) -> None:
        from googleapiclient.discovery import build

        self.service = build("drive", "v3", credentials=credentials, cache_discovery=False)

    def list(self, file_id: str) -> list[RawComment]:
        """Every open and resolved thread on the file, newest page first."""
        threads: list[RawComment] = []
        page = None
        while True:
            request = self.service.comments().list(
                fileId=file_id,
                fields=FIELDS,
                pageSize=PAGE_SIZE,
                pageToken=page,
                includeDeleted=False,
            )
            response = retrying(request.execute)
            threads += [_thread(item) for item in response.get("comments", [])]
            page = response.get("nextPageToken")
            if not page:
                return threads

    def create(self, file_id: str, text: str, anchor: str = "") -> RawComment:
        """Start a thread. An anchor Drive will not take is dropped rather than the comment."""
        if anchor:
            try:
                return self._create(file_id, {"content": text, "anchor": anchor})
            except Exception:  # noqa: BLE001 - Sheets anchors are undocumented and may change
                pass
        return self._create(file_id, {"content": text})

    def _create(self, file_id: str, body: dict) -> RawComment:
        created = (
            self.service.comments()
            .create(fileId=file_id, body=body, fields=COMMENT_FIELDS)
            .execute()
        )
        return _thread(created)

    def reply(self, file_id: str, comment_id: str, text: str) -> None:
        """Add a message to a thread."""
        self.service.replies().create(
            fileId=file_id, commentId=comment_id, body={"content": text}, fields="id"
        ).execute()

    def resolve(self, file_id: str, comment_id: str, text: str = "Resolved") -> None:
        """Close a thread, the way the Google Sheets Resolve button does.

        `text` is the reply that closes it, so saying why and closing is one call, not two.
        """
        # Resolving twice resolves once, so this one may safely be tried again.
        retrying(
            self.service.replies()
            .create(
                fileId=file_id,
                commentId=comment_id,
                body={"action": "resolve", "content": text},
                fields="id",
            )
            .execute
        )


def cell_anchor(tab_id: int, row: int, column: int) -> str:
    """The anchor that pins a comment to one cell of one tab.

    The shape is Google's, not ours, and is not documented; `CommentStore.create` falls
    back to an unanchored comment if Drive rejects it.
    """
    return json.dumps(
        {
            "type": "workbook-range",
            "uid": 0,
            "range": f"{tab_id}.{row}.{column}.{row}.{column}",
        }
    )


def anchored_cell(anchor: str) -> tuple[int, int, int] | None:
    """The tab id, row and column an anchor points at, or None if it points elsewhere."""
    try:
        data = json.loads(anchor or "{}")
    except ValueError:
        return None
    text = data.get("range", "") if isinstance(data, dict) else ""
    parts = text.split(".")
    if len(parts) < 3 or not all(part.lstrip("-").isdigit() for part in parts[:3]):
        return None
    return int(parts[0]), int(parts[1]), int(parts[2])


def _thread(item: dict) -> RawComment:
    return RawComment(
        id=item.get("id", ""),
        author=_author(item),
        created=_when(item.get("createdTime")),
        text=item.get("content", ""),
        resolved=bool(item.get("resolved")),
        anchor=item.get("anchor", "") or "",
        replies=tuple(
            RawReply(r.get("id", ""), _author(r), _when(r.get("createdTime")), r.get("content", ""))
            for r in item.get("replies", [])
            if r.get("content")
        ),
    )


def _author(item: dict) -> str:
    return (item.get("author") or {}).get("displayName", "Someone")


def _when(text: str | None) -> datetime:
    if not text:
        return datetime.now().astimezone()
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone()
