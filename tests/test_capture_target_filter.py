from scripts.capture_public_review_media import _filter_targets


def test_filter_targets_returns_all_when_env_missing(monkeypatch):
    monkeypatch.delenv("TARGET_PROFILE_IDS", raising=False)
    targets = [{"profile_id": "profile-1"}, {"profile_id": "profile-2"}]
    assert _filter_targets(targets) == targets


def test_filter_targets_keeps_only_requested_profiles(monkeypatch):
    monkeypatch.setenv("TARGET_PROFILE_IDS", "profile-2, profile-guayabal")
    targets = [
        {"profile_id": "profile-1"},
        {"profile_id": "profile-2"},
        {"profile_id": "profile-guayabal"},
    ]
    assert _filter_targets(targets) == [
        {"profile_id": "profile-2"},
        {"profile_id": "profile-guayabal"},
    ]
