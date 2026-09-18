"""Browsing Google Drive: the folders a user can pick, and the week sheets inside one."""

from dataclasses import dataclass

from brainwaves.model import WeekId

FOLDER_MIME = "application/vnd.google-apps.folder"
SHEET_MIME = "application/vnd.google-apps.spreadsheet"
ROOT = "root"
PAGE_SIZE = 200


@dataclass(frozen=True)
class DriveItem:
    """One folder or spreadsheet, as the picker shows it."""

    id: str
    name: str
    is_folder: bool


class Drive:
    """The Drive calls Brain Waves makes: list, create, move, rename."""

    def __init__(self, credentials) -> None:
        from googleapiclient.discovery import build

        self.service = build("drive", "v3", credentials=credentials, cache_discovery=False)

    def folders(self, parent: str = ROOT) -> list[DriveItem]:
        """Sub-folders of a folder, including shared drives the user can see from it."""
        return self._list(f"'{parent}' in parents and mimeType = '{FOLDER_MIME}'")

    def spreadsheets(self, parent: str) -> list[DriveItem]:
        """Spreadsheets directly inside a folder."""
        return self._list(f"'{parent}' in parents and mimeType = '{SHEET_MIME}'")

    def week_sheets(self, parent: str) -> dict[WeekId, DriveItem]:
        """The week sheets in a folder, keyed by the session and week their name spells."""
        found = {}
        for item in self.spreadsheets(parent):
            week_id = WeekId.parse(item.name)
            if week_id is not None:
                found[week_id] = item
        return found

    def name(self, file_id: str) -> str:
        """One file's name."""
        response = self.service.files().get(fileId=file_id, fields="name").execute()
        return response.get("name", "")

    def revision(self, file_id: str) -> str:
        """A short string that changes when the file does.

        This is the cheap question: a couple of hundred bytes, against the several hundred
        kilobytes of reading a board. Asking it often and reading only on a change is what
        makes other people's edits appear within a second or two.
        """
        response = self.service.files().get(fileId=file_id, fields="version,modifiedTime").execute()
        return f"{response.get('version', '')}/{response.get('modifiedTime', '')}"

    def move(self, file_id: str, parent: str) -> None:
        """Put a file in a folder, taking it out of wherever it was."""
        current = self.service.files().get(fileId=file_id, fields="parents").execute()
        self.service.files().update(
            fileId=file_id,
            addParents=parent,
            removeParents=",".join(current.get("parents", [])),
            fields="id",
        ).execute()

    def _list(self, query: str) -> list[DriveItem]:
        items: list[DriveItem] = []
        page = None
        while True:
            response = (
                self.service.files()
                .list(
                    q=f"{query} and trashed = false",
                    fields="nextPageToken, files(id, name, mimeType)",
                    orderBy="name",
                    pageSize=PAGE_SIZE,
                    pageToken=page,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
            items += [
                DriveItem(f["id"], f["name"], f["mimeType"] == FOLDER_MIME)
                for f in response.get("files", [])
            ]
            page = response.get("nextPageToken")
            if not page:
                return items
