"""Browsing Google Drive: the places a user can look, and the week sheets inside one.

Drive is not one tree. There is My Drive, there are the folders other people have shared
with you, and there is a shared drive for each team that has one — and a cabin act folder
is as likely to be in one of those as in anybody's own Drive. So the picker starts from a
list of places rather than from My Drive, and every query says it is happy to see items
from all of them.
"""

from dataclasses import dataclass

from brainwaves.google.retry import http_status, retrying
from brainwaves.model import WeekId

FOLDER_MIME = "application/vnd.google-apps.folder"
SHEET_MIME = "application/vnd.google-apps.spreadsheet"
PAGE_SIZE = 200

PLACES = ""  # the list of places itself, which is not a folder
MY_DRIVE = "root"
SHARED_WITH_ME = "sharedWithMe"

MY_DRIVE_NAME = "My Drive"
SHARED_WITH_ME_NAME = "Shared with me"


@dataclass(frozen=True)
class DriveItem:
    """One place, folder or spreadsheet, as the picker shows it."""

    id: str
    name: str
    is_folder: bool = True

    @property
    def can_hold_sheets(self) -> bool:
        """Whether this is somewhere a week sheet could actually live.

        "Shared with me" is a view rather than a folder: things appear in it, but nothing
        can be put in it.
        """
        return self.is_folder and self.id not in (PLACES, SHARED_WITH_ME)


class Drive:
    """The Drive calls Brain Waves makes: list places, list folders, list spreadsheets."""

    def __init__(self, credentials) -> None:
        from googleapiclient.discovery import build

        self.service = build("drive", "v3", credentials=credentials, cache_discovery=False)

    def places(self) -> list[DriveItem]:
        """Where a search can start: My Drive, what is shared with you, each shared drive."""
        return [
            DriveItem(MY_DRIVE, MY_DRIVE_NAME),
            DriveItem(SHARED_WITH_ME, SHARED_WITH_ME_NAME),
            *self.shared_drives(),
        ]

    def shared_drives(self) -> list[DriveItem]:
        """Every shared drive the user is a member of. A drive's id is also its root folder."""
        drives: list[DriveItem] = []
        page = None
        while True:
            request = self.service.drives().list(
                pageSize=100, fields="nextPageToken, drives(id, name)", pageToken=page
            )
            try:
                response = retrying(request.execute)
            except Exception:  # noqa: BLE001 - no shared drives is not a failure to report
                return drives
            drives += [DriveItem(d["id"], d["name"]) for d in response.get("drives", [])]
            page = response.get("nextPageToken")
            if not page:
                return drives

    def folders(self, parent: str) -> list[DriveItem]:
        """Sub-folders of a place or folder."""
        if parent == PLACES:
            return self.places()
        if parent == SHARED_WITH_ME:
            return self._list(f"sharedWithMe and mimeType = '{FOLDER_MIME}'", shared=True)
        return self._list(f"'{parent}' in parents and mimeType = '{FOLDER_MIME}'")

    def spreadsheets(self, parent: str) -> list[DriveItem]:
        """Spreadsheets directly inside a folder."""
        if not parent or parent == SHARED_WITH_ME:
            return []
        return self._list(f"'{parent}' in parents and mimeType = '{SHEET_MIME}'", folders=False)

    def week_sheets(self, parent: str) -> dict[WeekId, DriveItem]:
        """The week sheets in a folder, keyed by the session and week their name spells."""
        found = {}
        for item in self.spreadsheets(parent):
            week_id = WeekId.parse(item.name)
            if week_id is not None:
                found[week_id] = item
        return found

    def create_spreadsheet(self, name: str, parent: str) -> DriveItem:
        """Make an empty spreadsheet in a folder. Not tried again: that could make two."""
        made = (
            self.service.files()
            .create(
                body={"name": name, "mimeType": SHEET_MIME, "parents": [parent]},
                fields="id, name",
                supportsAllDrives=True,
            )
            .execute()
        )
        return DriveItem(made["id"], made.get("name", name), is_folder=False)

    def name(self, file_id: str) -> str:
        """One file's name."""
        request = self.service.files().get(fileId=file_id, fields="name", supportsAllDrives=True)
        return retrying(request.execute).get("name", "")

    def live_name(self, file_id: str) -> str | None:
        """A file's name, or None if it has been deleted or put in the trash.

        Sheets goes on reading and writing a spreadsheet in the trash as if nothing had
        happened, so Drive is the only one that can say a week sheet has gone.
        """
        request = self.service.files().get(
            fileId=file_id, fields="name, trashed", supportsAllDrives=True
        )
        try:
            found = retrying(request.execute)
        except Exception as error:
            if http_status(error) == 404:
                return None
            raise
        return None if found.get("trashed") else found.get("name", "")

    def _list(self, query: str, folders: bool = True, shared: bool = False) -> list[DriveItem]:
        """Run a Drive query across everything the user can see."""
        items: list[DriveItem] = []
        page = None
        while True:
            request = self.service.files().list(
                q=f"{query} and trashed = false",
                fields="nextPageToken, files(id, name, mimeType)",
                orderBy="name",
                pageSize=PAGE_SIZE,
                pageToken=page,
                # "Shared with me" is a view of the user's own corpus; everything else may
                # be in a shared drive, and asking for allDrives is how those come back.
                corpora="user" if shared else "allDrives",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            response = retrying(request.execute)
            items += [
                DriveItem(f["id"], f["name"], f["mimeType"] == FOLDER_MIME)
                for f in response.get("files", [])
            ]
            page = response.get("nextPageToken")
            if not page:
                return [item for item in items if item.is_folder == folders]
