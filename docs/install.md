# Install and set up

## For village leaders

1. Download the file for your computer from the
   [releases page](https://github.com/camp-augusta/brainwaves/releases):
   `brainwaves-windows.exe`, `brainwaves-macos` or `brainwaves-linux.tar.gz`.
2. Put it somewhere you will find it again, and open it. On macOS you may have to mark it
   runnable first (`chmod +x brainwaves-macos`). On Linux, unpack the archive where you
   want it to live and run the `install.sh` inside it once: that adds Brain Waves, with its
   icon, to your applications menu.
3. Press **Sign in with Google** and sign in with the account that can open the cabin act
   sheets.
4. Press **Link to Google Sheets** and walk down to the folder that holds the
   `Cabin Act Sorting - S2W1` sheets. It opens on everywhere you can look: **My Drive**,
   **Shared with me**, and each shared drive you are a member of — the camp folder is
   usually in one of the last two.
5. Set the session and week in the toolbar. Brain Waves remembers all of this.

That is the whole installation. There is no config file to put anywhere: everything that is
the same for everyone at camp — the Google client, the Skills doc — is built into the file
you downloaded, and the only things that differ from one person to the next are your
sign-in, your folder and your week, which Brain Waves remembers for you.

**Check for updates** in the top right asks GitHub whether a newer version is out, and
replaces the file you are running if you say yes. Restart it afterwards.

## For whoever sets camp up, once

Brain Waves acts as the person using it, so that a comment they write is theirs and a sheet
they cannot open stays closed. That needs a Google OAuth client, made once and built into
the releases.

1. In the [Google Cloud console](https://console.cloud.google.com), pick or make a project.
2. Enable the **Google Sheets API** and the **Google Drive API**. Nothing works without
   both.
3. Under **APIs and services - OAuth consent screen**, set the app up as **Internal** if
   camp has Google Workspace, or **External** with the village leaders added as test users.
   Ask for these scopes: `drive`, `spreadsheets`, `userinfo.email`.
4. Under **Credentials**, create an **OAuth client ID** of type **Desktop app**.
5. In the GitHub repository, under **Settings - Secrets and variables - Actions**, add
   `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. The release workflow builds those into
   every download. The Skills and Staff Categories documents already have camp's ids in
   `brainwaves/defaults.py`; `SKILLS_SHEET` and `CATEGORIES_SHEET` only need setting to
   build against different ones.

Push a tag (`git tag v0.2.0 && git push --tags`) and the release is built for all three
platforms with camp's settings inside.

!!! note
    A Google client secret for a desktop app is not confidential in the usual sense — it
    ships inside every copy of every desktop program that signs in to Google, and Google
    says as much. It is kept in a repository secret rather than in the code anyway, because
    a published one lets someone put camp's name on a consent screen of their own.

## Changing something without a new release

Settings can also come from a file, which overrides what was built in. Brain Waves looks for
`brainwaves.toml` beside the program — the simplest thing to hand someone — and then for
`config.toml` in the usual per-user config folder. `brainwaves where` prints which one is
in use and whether the Google client is set up.

```toml
# every one of these is optional; leave out what you are not changing

[google]
client_id     = "…….apps.googleusercontent.com"
client_secret = "……"

[sheets]
skills     = "1Woqx…"   # the Skills spreadsheet, for names and skills
categories = "1ldem…"   # the Staff Categories spreadsheet

[sync]
poll_seconds         = 3    # how often to read the board
comment_poll_seconds = 10   # how often to read comments, cabins and locations

[updates]
releases_url = "https://api.github.com/repos/camp-augusta/brainwaves/releases/latest"
```

Both documents fill the HERO chips: the Skills doc gives the staff names and the skills, the
Staff Categories doc gives the categories. Camp's own are built in, so these lines are only
needed to point Brain Waves at different ones. Without either, the chips still work — you
just type the names yourself.

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
| `brainwaves where` | Print which settings are in use and where the sign-in lives |
| `brainwaves template --csv folder` | Write the blank week template out as CSV files |
| `brainwaves template --folder <drive id>` | Create a blank week sheet in a Drive folder |
