"""
Statistics aggregation service for computing analytics from
playback activity events.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from services.data_models import (
    User,
    Item,
    Library,
    PlaybackActivity,
)


class StatsAggregator:
    def refresh_all_stats(session: Session) -> Dict[str, int]:
        """
        Refresh all denormalized statistics in a single operation.
        """
        play_counts = dict(
            session.query(
                PlaybackActivity.item_id,
                func.count(PlaybackActivity.id)
            )
            .group_by(PlaybackActivity.item_id)
            .all()
        )

        items_updated = 0
        if play_counts:
            rows = session.query(Item).filter(Item.jellyfin_id.in_(list(play_counts.keys()))).all()
            for it in rows:
                new_count = int(play_counts.get(it.jellyfin_id, 0))
                if it.play_count != new_count:
                    it.play_count = new_count
                items_updated += 1

        user_counts = dict(
            session.query(
                PlaybackActivity.user_id,
                func.count(PlaybackActivity.id)
            )
            .group_by(PlaybackActivity.user_id)
            .all()
        )
        users_updated = 0
        if user_counts:
            urows = session.query(User).filter(User.jellyfin_id.in_(list(user_counts.keys()))).all()
            for u in urows:
                new_total = int(user_counts.get(u.jellyfin_id, 0))
                if u.total_plays != new_total:
                    u.total_plays = new_total
                users_updated += 1

        libraries = session.query(Library).all()
        libs_updated = 0
        for lib in libraries:
            agg = session.query(
                func.count(Item.id),
                func.coalesce(func.sum(Item.runtime_seconds), 0),
                func.coalesce(func.sum(Item.size_bytes), 0),
                func.coalesce(func.sum(Item.runtime_seconds * Item.play_count), 0),
                func.coalesce(func.sum(Item.play_count), 0),
            ).filter(
                Item.library_id == lib.id,
                Item.archived == False
            ).one()

            total_files = int(agg[0] or 0)
            total_time_seconds = int(agg[1] or 0)
            size_bytes = int(agg[2] or 0)
            total_playback_seconds = int(agg[3] or 0)
            total_plays = int(agg[4] or 0)

            last = (
                session.query(PlaybackActivity, Item)
                .join(Item, PlaybackActivity.item_id == Item.jellyfin_id)
                .filter(Item.library_id == lib.id)
                .order_by(PlaybackActivity.activity_at.desc())
                .limit(1)
                .first()
            )
            last_played_name: Optional[str] = None
            if last and last[1]:
                last_played_name = last[1].name

            # Persist if changed
            changed = False
            if lib.total_files != total_files:
                lib.total_files = total_files
                changed = True
            if lib.total_time_seconds != total_time_seconds:
                lib.total_time_seconds = total_time_seconds
                changed = True
            if lib.size_bytes != size_bytes:
                lib.size_bytes = size_bytes
                changed = True
            if lib.total_playback_seconds != total_playback_seconds:
                lib.total_playback_seconds = total_playback_seconds
                changed = True
            if lib.total_plays != total_plays:
                lib.total_plays = total_plays
                changed = True
            if lib.last_played_item_name != last_played_name:
                lib.last_played_item_name = last_played_name
                changed = True

            if changed:
                session.merge(lib)
            libs_updated += 1

        return {
            "libraries_processed": libs_updated,
            "items_processed": items_updated,
            "users_processed": users_updated,
        }

    def get_top_items_by_plays(
        session: Session,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the most played items across all libraries.
        """
        q = (
            session.query(Item, Library)
            .join(Library, Item.library_id == Library.id)
            .order_by(Item.play_count.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "item_id": it.Item.jellyfin_id,
                "name": it.Item.name,
                "type": it.Item.type,
                "play_count": int(it.Item.play_count or 0),
                "library_id": it.Library.id,
                "library_name": it.Library.name,
            } for it in q
        ]

    def get_top_users_by_plays(
        session: Session,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the most active users by play count.
        """
        q = session.query(User).order_by(User.total_plays.desc()).limit(limit).all()
        return [
            {
                "user_id": u.jellyfin_id,
                "name": u.name,
                "total_plays": int(u.total_plays or 0),
            } for u in q
        ]

    def get_library_stats(
        session: Session,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all libraries with their play counts.
        """
        query = session.query(Library)
        if not include_archived:
            query = query.filter(Library.archived == False)

        out: List[Dict[str, Any]] = []
        for lib in query.all():
            series_count = 0
            episode_count = 0
            try:
                rows = (
                    session.query(func.lower(Item.type).label("type"), func.count(Item.id))
                    .filter(Item.library_id == lib.id, Item.archived == False)
                    .group_by(func.lower(Item.type))
                    .all()
                )
                for t, cnt in rows:
                    if t == "series":
                        series_count = int(cnt)
                    elif t == "episode":
                        episode_count = int(cnt)
            except Exception:
                series_count = 0
                episode_count = 0
            out.append({
                "id": lib.id,
                "jellyfin_id": lib.jellyfin_id,
                "name": lib.name,
                "type": lib.type,
                "image_url": lib.image_url,
                "tracked": lib.tracked,
                "total_plays": lib.total_plays,
                "total_time_seconds": lib.total_time_seconds,
                "total_files": lib.total_files,
                "size_bytes": lib.size_bytes,
                "total_playback_seconds": lib.total_playback_seconds,
                "last_played_item_name": lib.last_played_item_name,
                "archived": lib.archived,
                "item_count": int(lib.total_files or 0),
                "series_count": series_count,
                "episode_count": episode_count,
            })
        return out