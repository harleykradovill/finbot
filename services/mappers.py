from __future__ import annotations

from typing import Dict, Any, List, Optional


def map_user(jf_user: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Transform a Jellyfin user object into a User table row dict.
    """
    jf_id = (jf_user.get("Id") or "").strip()
    name = (jf_user.get("Name") or "").strip()
    
    if not jf_id or not name:
        return None
    
    return {
        "jellyfin_id": jf_id,
        "name": name,
        "is_admin": jf_user.get("Policy", {}).get("IsAdministrator", False),
    }


def map_users(jf_users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transform a list of Jellyfin users into User table row dicts.
    """
    results = []
    for user in jf_users:
        mapped = map_user(user)
        if mapped:
            results.append(mapped)
    return results


def map_library(jf_library: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Transform a Jellyfin library/media folder into a Library table row
    dict.
    """
    jf_id = (jf_library.get("Id") or "").strip()
    name = (
        jf_library.get("Name")
        or jf_library.get("Path")
        or ""
    ).strip()
    
    if not jf_id or not name:
        return None
    
    lib_type = jf_library.get("CollectionType") or jf_library.get("Type")
    
    image_tags = jf_library.get("ImageTags", {})
    primary_tag = image_tags.get("Primary")
    image_url = None
    if primary_tag:
        image_url = (
            f"/Items/{jf_id}/Images/Primary?tag={primary_tag}"
        )
    
    return {
        "jellyfin_id": jf_id,
        "name": name,
        "type": lib_type,
        "image_url": image_url,
    }


def map_libraries(
    jf_libraries: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Transform a list of Jellyfin libraries into Library table row dicts.
    """
    results = []
    for lib in jf_libraries:
        mapped = map_library(lib)
        if mapped:
            results.append(mapped)
    return results


def map_item(
    jf_item: Dict[str, Any],
    library_internal_id: int
) -> Optional[Dict[str, Any]]:
    """
    Transform a Jellyfin media item into an Item table row dict.
    """
    jf_id = (jf_item.get("Id") or "").strip()
    name = (jf_item.get("Name") or "").strip()
    
    if not jf_id or not name:
        return None
    
    item_type = jf_item.get("Type") or jf_item.get("MediaType")
    parent_id = jf_item.get("ParentId")

    # Extract runtime from RunTimeTicks (Jellyfin/.NET ticks = 100ns)
    runtime_seconds = 0
    rt = jf_item.get("RunTimeTicks") or jf_item.get("RunTimeTick") or 0
    try:
        rt_int = int(rt) if rt is not None else 0
        # 1 second = 10_000_000 .NET ticks
        runtime_seconds = int(rt_int / 10_000_000)
    except Exception:
        runtime_seconds = 0

    size_bytes = 0
    try:
        m_sources = jf_item.get("MediaSources") or []
        if isinstance(m_sources, list) and m_sources:
            for src in m_sources:
                if not isinstance(src, dict):
                    continue
                s = src.get("Size") or src.get("size") or 0
                try:
                    size_bytes += int(s)
                except Exception:
                    continue
    except Exception:
        size_bytes = 0

    return {
        "jellyfin_id": jf_id,
        "library_id": library_internal_id,
        "parent_id": parent_id,
        "name": name,
        "type": item_type,
        "runtime_seconds": runtime_seconds,
        "size_bytes": size_bytes,
    }

def map_items(
    jf_items: List[Dict[str, Any]],
    library_internal_id: int
) -> List[Dict[str, Any]]:
    """
    Transform a list of Jellyfin items into Item table row dicts.
    """
    results: List[Dict[str, Any]] = []
    for it in jf_items or []:
        mapped = map_item(it, library_internal_id)
        if mapped:
            results.append(mapped)
    return results

def map_playback_event(
    jf_event: Dict[str, Any],
    username: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Transform a Jellyfin playback event into a PlaybackActivity table row dict.
    """
    user_id = (jf_event.get("UserId") or "").strip()
    item_id = (jf_event.get("ItemId") or "").strip()

    if not user_id or not item_id:
        return None

    activity_log_id = jf_event.get("Id") or jf_event.get("ActivityId")

    event_name = (jf_event.get("Name") or "").strip()
    event_overview = (
        jf_event.get("ShortOverview")
        or jf_event.get("Overview")
        or ""
    ).strip()

    activity_timestamp = jf_event.get("Date") or jf_event.get("ActivityDate")
    activity_at = None
    if activity_timestamp is not None:
        try:
            if isinstance(activity_timestamp, (int, float)):
                ts = int(activity_timestamp)
                if ts > 10**12:
                    ts = int(ts / 1000)
                activity_at = ts
            else:
                from datetime import datetime
                s = str(activity_timestamp).strip()
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                activity_at = int(dt.timestamp())
        except Exception:
            import time as _time
            activity_at = int(_time.time())
    else:
        import time as _time
        activity_at = int(_time.time())

    session_id = jf_event.get("SessionId") or jf_event.get("Session")
    client = jf_event.get("Client") or jf_event.get("ClientName")
    device = jf_event.get("Device") or jf_event.get("DeviceName") or jf_event.get(
        "DeviceId"
    )

    trans_info = jf_event.get("TranscodingInfo") or {}
    is_transcoding = bool(
        jf_event.get("IsTranscoding")
        or trans_info
        or jf_event.get("IsVideoTranscoding")
        or jf_event.get("IsAudioTranscoding")
    )
    transcode_video = bool(
        trans_info.get("IsVideoTranscoding")
        or jf_event.get("IsVideoTranscoding")
    )
    transcode_audio = bool(
        trans_info.get("IsAudioTranscoding")
        or jf_event.get("IsAudioTranscoding")
    )

    play_method = (
        jf_event.get("PlayMethod")
        or jf_event.get("Method")
        or (trans_info.get("Method") if isinstance(trans_info, dict) else None)
    )

    return {
        "activity_log_id": activity_log_id,
        "user_id": user_id,
        "item_id": item_id,
        "event_name": event_name,
        "event_overview": event_overview,
        "activity_at": activity_at,
        "username_denorm": username,
        "session_id": session_id,
        "client": client,
        "device": device,
        "is_transcoding": is_transcoding,
        "transcode_video": transcode_video,
        "transcode_audio": transcode_audio,
        "play_method": play_method,
    }


def map_playback_events(
    jf_events: List[Dict[str, Any]],
    user_lookup: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """
    Transform a list of Jellyfin playback events into PlaybackActivity
    table row dicts.
    """
    results: List[Dict[str, Any]] = []
    for event in jf_events:
        user_id = (event.get("UserId") or "").strip()
        username = None
        if user_lookup and user_id:
            username = user_lookup.get(user_id)

        mapped = map_playback_event(event, username)
        if mapped:
            results.append(mapped)
    return results