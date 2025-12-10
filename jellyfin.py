"""
Lightweight Jellyfin client that reads persisted settings and performs
authenticated requests to the Jellyfin REST API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from settings_store import SettingsService


class JellyfinClient:
    """
    A minimal client for Jellyfin REST API backed by SettingsService.
    """

    def __init__(self, settings: SettingsService) -> None:
        self._settings = settings

    def _read_settings(self) -> Tuple[str, str, str, str]:
        """
        Read settings and normalize scheme/host.
        """
        s = self._settings.get()
        host = (s.get("jf_host") or "").strip()
        port = (s.get("jf_port") or "").strip()
        token = (s.get("jf_api_key") or "").strip()
        scheme = "http"

        if host.startswith(("http://", "https://")):
            if host.startswith("https://"):
                scheme = "https"
                host = host.removeprefix("https://")
            else:
                host = host.removeprefix("http://")

        return scheme, host, port, token

    def _build_url(self, path: str) -> Optional[str]:
        """
        Construct a full URL for a given Jellyfin path.
        """
        scheme, host, port, token = self._read_settings()
        if not host or not port or not port.isdigit() or not token:
            return None
        base = f"{scheme}://{host}:{port}"
        return f"{base}{path}"

    def _get(self, path: str) -> Dict[str, Any]:
        """
        Perform a GET request to Jellyfin and return parsed JSON.
        """
        url = self._build_url(path)
        if not url:
            return {
                "ok": False,
                "status": 400,
                "message": "Missing or invalid host/port/token in settings.",
            }

        # Read token again for header
        _, _, _, token = self._read_settings()

        req = Request(url, method="GET")
        req.add_header("X-Emby-Token", token)
        req.add_header("Accept", "application/json")

        try:
            with urlopen(req, timeout=5.0) as resp:
                status = getattr(resp, "status", 200)
                data = resp.read()
                import json
                try:
                    parsed = json.loads(data.decode("utf-8"))
                except Exception:
                    parsed = {}

                return {
                    "ok": 200 <= status < 300,
                    "status": status,
                    "data": parsed,
                }
        except HTTPError as he:
            return {
                "ok": False,
                "status": he.code,
                "message": f"HTTP error from Jellyfin ({he.code}): {he.reason or 'Unknown'}",
            }
        except URLError as ue:
            reason = getattr(ue, "reason", "Unknown")
            return {
                "ok": False,
                "status": 0,
                "message": f"Network error: {reason}",
            }
        except Exception as exc:
            return {
                "ok": False,
                "status": 0,
                "message": f"Unexpected error: {str(exc)}",
            }

    # Public API

    def validate_connection(self) -> Dict[str, Any]:
        """
        Calls /System/Info to validate connectivity and credentials.
        """
        return self._get("/System/Info")

    def system_info(self) -> Dict[str, Any]:
        """
        Returns Jellyfin system info
        """
        return self._get("/System/Info")

    def users(self) -> Dict[str, Any]:
        """
        Returns list of users
        """
        return self._get("/Users")

    def libraries(self) -> Dict[str, Any]:
        """
        Returns media folders
        """
        return self._get("/Library/MediaFolders")
    
    def library_items(self, library_id: str) -> Dict[str, Any]:
        return self._get(f"/Items?ParentId={library_id}&Recursive=true&Limit=0")

    def library_stats(self, library_id: str) -> Dict[str, Any]:
        result = self.library_items(library_id)
        if result.get("ok") and isinstance(result.get("data"), dict):
            return {
                "ok": True,
                "item_count": result["data"].get("TotalRecordCount", 0)
            }
        return {"ok": False, "item_count": 0}


def create_client(settings_service: SettingsService) -> JellyfinClient:
    """
    Factory to create a JellyfinClient from a settings_store.
    """
    return JellyfinClient(settings_service)