# ...existing code...
from services.repository import Repository


def test_library_stats_counts_from_db() -> None:
    """
    Ensure library stats endpoint uses DB counts for items, series,
    and episodes (no Jellyfin calls).
    """
    repo = Repository(database_url="sqlite:///:memory:")

    lib = {"jellyfin_id": "lib1", "name": "Test Library", "type": "tvshows", "image_url": None}
    assert repo.upsert_libraries([lib]) == 1

    libs = repo.list_libraries(include_archived=True)
    created = next((l for l in libs if l["jellyfin_id"] == "lib1"), None)
    assert created is not None
    lib_id = created["id"]

    items = [
        {
            "jellyfin_id": "series1",
            "library_id": lib_id,
            "parent_id": None,
            "name": "Series One",
            "type": "series",
            "runtime_seconds": 0,
            "size_bytes": 0,
        },
        {
            "jellyfin_id": "ep1",
            "library_id": lib_id,
            "parent_id": "series1",
            "name": "Episode 1",
            "type": "episode",
            "runtime_seconds": 0,
            "size_bytes": 0,
        },
    ]
    assert repo.upsert_items(items) == 2

    repo.refresh_play_stats()

    stats = repo.get_library_stats(include_archived=True)
    s = next((x for x in stats if x["jellyfin_id"] == "lib1"), None)
    assert s is not None
    assert s["item_count"] == 2
    assert s["series_count"] == 1
    assert s["episode_count"] == 1