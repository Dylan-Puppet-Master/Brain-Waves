from brainwaves.config import Config, State, load_config, load_state, save_state, with_week


def test_a_missing_config_file_gives_defaults(tmp_path):
    config = load_config(tmp_path / "nothing.toml")
    assert config == Config()
    assert not config.has_client


def test_a_config_file_is_read(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        """
        [google]
        client_id = "id"
        client_secret = "secret"

        [sheets]
        skills = "sheet-id"
        skills_tab = "Skills 2026"

        [sync]
        poll_seconds = 30

        [updates]
        releases_url = "https://example.invalid/latest"
        """
    )
    config = load_config(path)
    assert config.has_client
    assert (config.client_id, config.skills_sheet, config.skills_tab) == (
        "id",
        "sheet-id",
        "Skills 2026",
    )
    assert config.poll_seconds == 30
    assert config.releases_url == "https://example.invalid/latest"


def test_state_survives_a_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAINWAVES_DATA", str(tmp_path))
    save_state(State("folder-id", "Cabin Acts 2026", 2, 3))
    assert load_state() == State("folder-id", "Cabin Acts 2026", 2, 3)


def test_a_corrupt_state_file_gives_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAINWAVES_DATA", str(tmp_path))
    (tmp_path / "state.json").write_text("{ not json")
    assert load_state() == State()


def test_an_unknown_key_in_the_state_file_gives_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("BRAINWAVES_DATA", str(tmp_path))
    (tmp_path / "state.json").write_text('{"folder_id": "a", "surprise": 1}')
    assert load_state() == State()


def test_with_week_changes_only_the_week():
    state = State("folder-id", "name", 1, 1)
    assert with_week(state, 3, 2) == State("folder-id", "name", 3, 2)


def test_a_download_with_settings_built_in_needs_no_config_file(tmp_path, monkeypatch):
    """A village leader opens one file and signs in. That is the whole installation."""
    monkeypatch.setattr(
        "brainwaves.built_in.SETTINGS",
        {"client_id": "id", "client_secret": "secret", "skills_sheet": "sheet"},
    )
    monkeypatch.setenv("BRAINWAVES_CONFIG", str(tmp_path / "absent.toml"))
    config = load_config()
    assert config.has_client
    assert config.skills_sheet == "sheet"
    assert config.poll_seconds == Config().poll_seconds


def test_a_config_file_overrides_what_was_built_in(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "brainwaves.built_in.SETTINGS",
        {"client_id": "built", "client_secret": "secret", "skills_sheet": "built-sheet"},
    )
    path = tmp_path / "brainwaves.toml"
    path.write_text('[sheets]\nskills = "this-one-instead"\n')
    config = load_config(path)
    assert config.skills_sheet == "this-one-instead"
    assert config.client_id == "built"  # what the file did not mention is kept


def test_settings_beside_the_program_are_found(tmp_path, monkeypatch):
    from brainwaves import config as settings

    beside, personal = tmp_path / "beside", tmp_path / "personal"
    beside.mkdir()
    personal.mkdir()
    monkeypatch.delenv("BRAINWAVES_CONFIG", raising=False)
    monkeypatch.setattr(settings, "program_folder", lambda: beside)
    monkeypatch.setattr(settings, "user_config_path", lambda _name: personal)
    (beside / "brainwaves.toml").write_text('[sheets]\nskills = "beside-the-program"\n')
    assert settings.load_config().skills_sheet == "beside-the-program"
    assert settings.config_path() == beside / "brainwaves.toml"


def test_a_personal_config_file_wins_over_one_beside_the_program(tmp_path, monkeypatch):
    from brainwaves import config as settings

    beside, personal = tmp_path / "beside", tmp_path / "personal"
    beside.mkdir()
    personal.mkdir()
    monkeypatch.delenv("BRAINWAVES_CONFIG", raising=False)
    monkeypatch.setattr(settings, "program_folder", lambda: beside)
    monkeypatch.setattr(settings, "user_config_path", lambda _name: personal)
    (beside / "brainwaves.toml").write_text(
        '[sheets]\nskills = "beside"\n[sync]\npoll_seconds = 9\n'
    )
    (personal / "config.toml").write_text('[sheets]\nskills = "personal"\n')
    config = settings.load_config()
    assert config.skills_sheet == "personal"
    assert config.poll_seconds == 9  # what it did not mention is still kept


def test_camps_real_credentials_are_not_committed():
    """Built-in settings are filled by the release build, never checked in.

    A published desktop client secret is not a disaster, but it does let someone put camp's
    name on a consent screen of their own.
    """
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / "brainwaves" / "built_in.py").read_text()
    body = source.split("SETTINGS", 1)[1]
    assert ".apps.googleusercontent.com" not in body
    assert "GOCSPX-" not in body
