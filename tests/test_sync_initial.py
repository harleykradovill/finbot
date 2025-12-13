import time

from services.repository import Repository
from services.sync_service import SyncService


class FakeJellyfinClient:
    def users(self):
        return {"ok": True, "data": [{"Id": "1", "Name": "admin"}]}

    def libraries(self):
        return {
            "ok": True,
            "data": [
                {"Id": "lib_movies", "Name": "Movies", "CollectionType": "movies"},
                {"Id": "lib_playlists", "Name": "Playlists", "CollectionType": "playlists"},
                {"Id": "lib_tv", "Name": "TV Shows", "CollectionType": "tvshows"},
                {"Id": "lib_mini", "Name": "Mini Series", "CollectionType": "mini series"},
            ],
        }

    def library_items(self, library_id: str):
        return {"ok": True, "data": {"Items": []}}

    def get_activity_log(self, *args, **kwargs):
        return {"ok": True, "data": []}


def test_initial_auto_tracks_media_libraries() -> None:
    repo = Repository(database_url="sqlite:///:memory:")
    fake = FakeJellyfinClient()
    sync = SyncService(jellyfin_client=fake, repository=repo)

    res = sync.sync_initial()
    assert res is not None

    libs = {l["jellyfin_id"]: l for l in repo.list_libraries()}
    assert libs["lib_movies"]["tracked"] is True
    assert libs["lib_tv"]["tracked"] is True


def test_manual_full_sync_does_not_auto_track() -> None:
    repo = Repository(database_url="sqlite:///:memory:")
    fake = FakeJellyfinClient()
    sync = SyncService(jellyfin_client=fake, repository=repo)

    res = sync.sync_full(auto_track=False)
    assert res is not None

    libs = {l["jellyfin_id"]: l for l in repo.list_libraries()}
    assert libs["lib_movies"]["tracked"] is False
    assert libs["lib_tv"]["tracked"] is False