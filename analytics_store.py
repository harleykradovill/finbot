# Python
"""
Analytics storage using SQLAlchemy for Jellyfin users and libraries.
Provides simple upsert methods to persist pulled data once per button click.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, BigInteger, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

AnalyticsBase = declarative_base()


class JfUserStat(AnalyticsBase):
    """
    Table storing Jellyfin user analytics snapshot.
    """
    __tablename__ = "jf_user_stats"
    id = Column(Integer, primary_key=True)
    jellyfin_id = Column(String(128), nullable=False)
    name = Column(String(255), nullable=False)
    play_count = Column(BigInteger, default=0)
    last_play = Column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint("jellyfin_id", name="uq_user_jf_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "jellyfin_id": self.jellyfin_id,
            "name": self.name,
            "play_count": int(self.play_count or 0),
            "last_play": self.last_play,
        }


class JfLibraryStat(AnalyticsBase):
    """
    Table storing Jellyfin library analytics snapshot and track flag.
    """
    __tablename__ = "jf_library_stats"
    id = Column(Integer, primary_key=True)
    jellyfin_id = Column(String(128), nullable=False)
    name = Column(String(255), nullable=False)
    image_url = Column(String(1024), nullable=True)
    tracked = Column(Boolean, default=False)
    item_count = Column(BigInteger, default=0)
    play_count = Column(BigInteger, default=0)

    __table_args__ = (
        UniqueConstraint("jellyfin_id", name="uq_lib_jf_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "jellyfin_id": self.jellyfin_id,
            "name": self.name,
            "image_url": self.image_url,
            "tracked": bool(self.tracked),
            "item_count": int(self.item_count or 0),
            "play_count": int(self.play_count or 0),
        }


@dataclass
class AnalyticsService:
    """
    Service for accessing analytics database (separate file).
    Default: sqlite:///analytics.db
    """
    database_url: str = "sqlite:///analytics.db"

    def __post_init__(self) -> None:
        self.engine = create_engine(self.database_url, future=True)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        AnalyticsBase.metadata.create_all(self.engine)

    def _session(self) -> Session:
        return self.SessionLocal()

    # Users

    def upsert_users(self, users: List[Dict[str, Any]]) -> int:
        """
        Upsert users by `jellyfin_id`. Inserts new or updates name/play stats.
        """
        if not users:
            return 0
        count = 0
        with self._session() as session:
            for u in users:
                jf_id = (u.get("Id") or u.get("id") or "").strip()
                name = (u.get("Name") or u.get("name") or "").strip()
                if not jf_id or not name:
                    continue
                row = session.query(JfUserStat).filter_by(jellyfin_id=jf_id).first()
                if not row:
                    row = JfUserStat(jellyfin_id=jf_id, name=name)
                else:
                    row.name = name
                if "PlayCount" in u:
                    try:
                        row.play_count = int(u["PlayCount"] or 0)
                    except Exception:
                        pass
                if "LastPlayed" in u:
                    row.last_play = str(u["LastPlayed"]) if u["LastPlayed"] else None
                session.add(row)
                count += 1
            session.commit()
        return count

    def list_users(self) -> List[Dict[str, Any]]:
        """
        Return all user analytics rows as dicts.
        """
        with self._session() as session:
            return [r.to_dict() for r in session.query(JfUserStat).all()]

    # Libraries

    def upsert_libraries(self, libs: List[Dict[str, Any]]) -> int:
        """
        Upsert libraries by `jellyfin_id`. Preserve existing `tracked`.
        """
        if not libs:
            return 0
        count = 0
        with self._session() as session:
            for l in libs:
                jf_id = (l.get("Id") or l.get("id") or "").strip()
                name = (l.get("Name") or l.get("name") or l.get("Path") or "").strip()
                image = l.get("ImageUrl") or l.get("image_url") or None
                if not jf_id or not name:
                    continue
                row = session.query(JfLibraryStat).filter_by(jellyfin_id=jf_id).first()
                if not row:
                    row = JfLibraryStat(jellyfin_id=jf_id, name=name)
                else:
                    row.name = name
                row.image_url = image
                # Optional counters if provided by upstream
                for key, attr in (("ItemCount", "item_count"), ("PlayCount", "play_count")):
                    if key in l:
                        try:
                            setattr(row, attr, int(l[key] or 0))
                        except Exception:
                            pass
                session.add(row)
                count += 1
            session.commit()
        return count

    def list_libraries(self) -> List[Dict[str, Any]]:
        with self._session() as session:
            return [r.to_dict() for r in session.query(JfLibraryStat).all()]

    def set_library_tracked(self, jellyfin_id: str, tracked: bool) -> Optional[Dict[str, Any]]:
        """
        Set the tracked flag for a library by Jellyfin ID.
        Returns updated row dict or None if not found.
        """
        with self._session() as session:
            row = session.query(JfLibraryStat).filter_by(jellyfin_id=jellyfin_id).first()
            if not row:
                return None
            row.tracked = bool(tracked)
            session.add(row)
            session.commit()
            session.refresh(row)
            return row.to_dict()
