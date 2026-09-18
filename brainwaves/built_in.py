"""Camp's own settings, built into this copy of Brain Waves.

Nothing here is personal: the Google client, the Skills doc and the update feed are the
same for every village leader. Building them in is what lets someone download one file and
open it, with no config file to put anywhere.

In the repository these are blank, so a source checkout reads `config.toml` as before. The
release workflow fills them in from the repository's secrets before packaging; see
`tools/build_settings.py` and docs/install.md.

A Google client secret for a desktop app is not a secret in the usual sense — it ships
inside every copy of every desktop program that signs in to Google, and Google says as
much. It is kept out of the repository anyway, because a published one invites someone to
put camp's name on a consent screen of their own.
"""

SETTINGS: dict[str, str] = {}
