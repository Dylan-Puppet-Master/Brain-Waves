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
