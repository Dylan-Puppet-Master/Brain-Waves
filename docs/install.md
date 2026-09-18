# Install and set up

## For village leaders

1. Download the file for your computer from the
   [releases page](https://github.com/camp-augusta/brainwaves/releases):
   `brainwaves-windows.exe`, `brainwaves-macos` or `brainwaves-linux`.
2. Put it somewhere you will find it again, and open it. On macOS and Linux you may have
   to mark it runnable first (`chmod +x brainwaves-macos`).
3. Press **Sign in with Google** and sign in with the account that can open the cabin act
   sheets.
4. Press **Link to Google Sheets** and walk down your Drive to the folder that holds the
   `Cabin Act Sorting - S2W1` sheets.
5. Set the session and week in the toolbar. Brain Waves remembers all of this.

**Check for updates** in the top right asks GitHub whether a newer version is out, and
replaces the file you are running if you say yes. Restart it afterwards.

## For whoever sets camp up, once

Brain Waves acts as the person using it, so that a comment they write is theirs and a sheet
they cannot open stays closed. That needs a Google OAuth client, which is made once and
shared with the village leaders in their config file.

1. In the [Google Cloud console](https://console.cloud.google.com), pick or make a project.
2. Enable the **Google Sheets API** and the **Google Drive API**.
3. Under **APIs and services - OAuth consent screen**, set the app up as **Internal** if
   camp has Google Workspace, or **External** with the village leaders added as test users.
   Ask for these scopes: `drive`, `spreadsheets`, `userinfo.email`.
4. Under **Credentials**, create an **OAuth client ID** of type **Desktop app**. Note the
   client id and client secret.
5. Write the config file on each village leader's computer. Brain Waves prints where it
   looks:

```
brainwaves where
```

```toml
# ~/.config/brainwaves/config.toml on Linux
# ~/Library/Application Support/brainwaves/config.toml on macOS
# %LOCALAPPDATA%\brainwaves\config.toml on Windows

[google]
client_id     = "…….apps.googleusercontent.com"
client_secret = "……"

[sheets]
skills = "1Woqx_vthAAbGh-CSGFwgMDooqhkt0PWV1XKLiNqiJvU"  # the Skills spreadsheet id

[sync]
poll_seconds = 15   # how often to read the sheet again

[updates]
releases_url = "https://api.github.com/repos/camp-augusta/brainwaves/releases/latest"
```

The Skills doc is what fills the HERO chips. Without it the chips still work, but you type
the names yourself.

## Running from source

```
git clone https://github.com/camp-augusta/brainwaves
cd brainwaves
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
brainwaves
```

| Command | Does |
|---|---|
| `brainwaves` | Open the window |
| `brainwaves sign-in` | Sign in to Google without opening the window |
| `brainwaves sign-out` | Forget the saved sign-in |
| `brainwaves where` | Print where settings and the saved sign-in live |
| `brainwaves template --csv folder` | Write the blank week template out as CSV files |
| `brainwaves template --folder <drive id>` | Create a blank week sheet in a Drive folder |
