"""
Provides an application factory that constructs and configures a
Flask instance used to server the Borealis site.
"""

from typing import Optional, Dict
import time

try:
    from flask import Flask, Response, render_template, jsonify, request, send_from_directory
except Exception as exc:
    raise RuntimeError(
        "Flask is required to run the local config site. "
        "Install with: pip install Flask"
    ) from exc


def create_app(test_config: Optional[Dict] = None) -> "Flask":
    """
    Create and configure the Borealis Flask application.
    """
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )

    app.config.setdefault("DEBUG", False)
    app.config.setdefault("PORT", 2929)
    app.config.setdefault("DATABASE_URL", "sqlite:///borealis.db")
    app.config.setdefault("ENCRYPTION_KEY_PATH", "secret.key")
    app.config.setdefault("DATA_DATABASE_URL", "sqlite:///borealis_data.db")

    if test_config:
        app.config.update(test_config)
        if app.config.get("DEBUG", False):
            if "DATABASE_URL" not in test_config:
                app.config["DATABASE_URL"] = "sqlite:///:memory:"
            if "ENCRYPTION_KEY_PATH" not in test_config:
                app.config["ENCRYPTION_KEY_PATH"] = ":memory:"
            if "DATA_DATABASE_URL" not in test_config:
                app.config["DATA_DATABASE_URL"] = "sqlite:///:memory:"

    from services.settings_store import SettingsService
    svc = SettingsService(
        database_url=app.config["DATABASE_URL"],
        encryption_key_path=app.config["ENCRYPTION_KEY_PATH"],
    )

    from services.repository import Repository
    repo = Repository(
        database_url=app.config["DATA_DATABASE_URL"]
    )

    from services.jellyfin import create_client
    jf = create_client(svc)

    from services.sync_service import SyncService
    sync = SyncService(
        jellyfin_client=jf,
        repository=repo
    )

    from services.sync_scheduler import SyncScheduler

    sync_scheduler = SyncScheduler(
        sync_service=sync,
        interval_seconds=1800  # 30 min
    )

    if not app.config.get("DEBUG"):
        sync_scheduler.start()

    import atexit
    
    def cleanup():
        """
        Cleanup function called when app shuts down.
        """
        try:
            sync_scheduler.stop()
        except Exception:
            pass
        try:
            svc.engine.dispose()
        except Exception:
            pass
        try:
            repo.engine.dispose()
        except Exception:
            pass
    
    atexit.register(cleanup)

    @app.get("/assets/<path:filename>")
    def assets(filename: str) -> Response:
        if filename.startswith("js/"):
            return send_from_directory(
                "static/js",
                filename.removeprefix("js/")
            )
        return send_from_directory("assets", filename)

    @app.get("/api/settings")
    def get_settings() -> Response:
        return jsonify(svc.get()), 200
    
    @app.put("/api/settings")
    def update_settings() -> Response:
        payload = request.get_json(silent=True) or {}
        
        # Get current settings before update
        current_settings = svc.get()
        had_server = (
            current_settings.get("jf_host")
            and current_settings.get("jf_port")
            and current_settings.get("jf_api_key")
        )
        
        # Update settings
        updated = svc.update(payload)
        
        # Check if server is being added for the first time
        has_server = (
            updated.get("jf_host")
            and updated.get("jf_port")
            and updated.get("jf_api_key")
        )
        
        # If adding server for first time, trigger initial sync
        if not had_server and has_server:
            # Mark that we're starting initial sync to prevent 
            # scheduler from also triggering it
            svc.set_last_activity_log_sync(int(time.time()))

            try:
                current = svc.get_last_activity_log_sync()
                print(f"DEBUG: last_activity_log_sync persisted -> {current}")
            except Exception:
                print("DEBUG: failed to read back last_activity_log_sync")
            
            # Trigger sync_initial in background thread
            import threading
            def run_initial_sync():
                try:
                    sync.sync_initial()
                except Exception as exc:
                    import traceback
                    traceback.print_exc()
            
            sync_thread = threading.Thread(
                target=run_initial_sync,
                daemon=True
            )
            sync_thread.start()
        
        return jsonify(updated), 200
    
    @app.teardown_appcontext
    def _dispose_db(_exc: Optional[BaseException]) -> None:
        try:
            svc.engine.dispose()
        except Exception:
            pass
        try:
            repo.engine.dispose()
        except Exception:
            pass

    @app.get("/api/test-connection")
    def test_connection() -> Response:
        """
        Test Jellyfin connectivity using persisted settings.
        """
        from urllib.request import Request, urlopen
        from urllib.error import URLError, HTTPError

        settings = svc.get()
        host = (settings.get("jf_host") or "").strip()
        port = (settings.get("jf_port") or "").strip()
        token = (settings.get("jf_api_key") or "").strip()

        if not host or not port or not token:
            return jsonify({
                "ok": False,
                "status": 400,
                "message": "Missing host, port, or API key in settings."
            }), 200

        if not port.isdigit():
            return jsonify({
                "ok": False,
                "status": 400,
                "message": "Stored port must be numeric."
            }), 200

        scheme = "http"
        if host.startswith(("http://", "https://")):
            if host.startswith("https://"):
                scheme = "https"
                host = host.removeprefix("https://")
            elif host.startswith("http://"):
                scheme = "http"
                host = host.removeprefix("http://")

        url = f"{scheme}://{host}:{port}/System/Info"

        req = Request(url, method="GET")
        req.add_header("X-Emby-Token", token)
        req.add_header("Accept", "application/json")

        try:
            with urlopen(req, timeout=3.0) as resp:
                status = getattr(resp, "status", 200)
                if 200 <= status < 300:
                    return jsonify({
                        "ok": True,
                        "status": status,
                        "message": "Connection successful."
                    }), 200
                return jsonify({
                    "ok": False,
                    "status": status,
                    "message": f"Jellyfin returned status {status}."
                }), 200
        except HTTPError as he:
            return jsonify({
                "ok": False,
                "status": he.code,
                "message": (
                    f"HTTP error from Jellyfin ({he.code}): "
                    f"{he.reason or 'Unknown'}"
                )
            }), 200
        except URLError as ue:
            reason = getattr(ue, "reason", "Unknown")
            return jsonify({
                "ok": False,
                "status": 0,
                "message": f"Network error: {reason}"
            }), 200
        except Exception as exc:
            return jsonify({
                "ok": False,
                "status": 0,
                "message": f"Unexpected error: {str(exc)}"
            }), 200
        
    @app.post("/api/test-connection-with-credentials")
    def test_connection_with_credentials() -> Response:
        """
        Test Jellyfin connectivity with provided credentials.
        """
        from urllib.request import Request, urlopen
        from urllib.error import URLError, HTTPError

        payload = request.get_json(silent=True) or {}
        host = (payload.get("jf_host") or "").strip()
        port = (payload.get("jf_port") or "").strip()
        token = (payload.get("jf_api_key") or "").strip()

        if not host or not port or not token:
            return jsonify({
                "ok": False,
                "status": 400,
                "message": (
                    "Missing host, port, or API key."
                )
            }), 200

        if not port.isdigit():
            return jsonify({
                "ok": False,
                "status": 400,
                "message": "Port must be numeric."
            }), 200

        # Parse host to handle http:// or https:// prefixes
        scheme = "http"
        if host.startswith(("http://", "https://")):
            if host.startswith("https://"):
                scheme = "https"
                host = host.removeprefix("https://")
            elif host.startswith("http://"):
                scheme = "http"
                host = host.removeprefix("http://")

        url = f"{scheme}://{host}:{port}/System/Info"

        req = Request(url, method="GET")
        req.add_header("X-Emby-Token", token)
        req.add_header("Accept", "application/json")

        try:
            with urlopen(req, timeout=3.0) as resp:
                status = getattr(resp, "status", 200)
                if 200 <= status < 300:
                    return jsonify({
                        "ok": True,
                        "status": status,
                    }), 200
                return jsonify({
                    "ok": False,
                    "status": status,
                    "message": (
                        f"Jellyfin returned status {status}."
                    )
                }), 200
        except HTTPError as he:
            return jsonify({
                "ok": False,
                "status": he.code,
                "message": (
                    f"HTTP error from Jellyfin ({he.code}): "
                    f"{he.reason or 'Unknown'}"
                )
            }), 200
        except URLError as ue:
            reason = getattr(ue, "reason", "Unknown")
            return jsonify({
                "ok": False,
                "status": 0,
                "message": f"Network error: {reason}"
            }), 200
        except Exception as exc:
            return jsonify({
                "ok": False,
                "status": 0,
                "message": f"Unexpected error: {str(exc)}"
            }), 200

    @app.get("/")
    def index() -> Response:
        return render_template("index.html"), 200
    
    @app.get("/users")
    def users() -> Response:
        return render_template("users.html"), 200
    
    @app.get("/libraries")
    def libraries() -> Response:
        return render_template("libraries.html"), 200
    
    @app.get("/settings")
    def settings() -> Response:
        return render_template("settings.html"), 200

    @app.get("/api/jellyfin/system-info")
    def api_jf_system_info() -> Response:
        result = jf.system_info()
        return jsonify(result), 200

    @app.get("/api/jellyfin/users")
    def api_jf_users() -> Response:
        """
        Fetches users and upserts to repository.
        """
        result = jf.users()
        if result and result.get("ok") and isinstance(
            result.get("data"), list
        ):
            try:
                from services.mappers import map_users
                mapped = map_users(result["data"])
                repo.upsert_users(mapped)
            except Exception:
                pass
        return jsonify(result), 200

    @app.get("/api/jellyfin/libraries")
    def api_jf_libraries() -> Response:
        """
        Fetches libraries with item counts and upserts to repository.
        """
        result = jf.libraries()

        data = result.get("data")
        if result and result.get("ok"):
            # Normalize Items shape
            if isinstance(data, dict) and isinstance(
                data.get("Items"), list
            ):
                flat = data["Items"]
            elif isinstance(data, list):
                flat = data
            else:
                flat = []

            try:
                import concurrent.futures

                id_map = [
                    (idx, lib.get("Id"))
                    for idx, lib in enumerate(flat)
                    if lib.get("Id")
                ]

                if id_map:
                    max_workers = min(8, len(id_map))
                    with concurrent.futures.ThreadPoolExecutor(
                        max_workers=max_workers
                    ) as ex:
                        future_to_idx = {
                            ex.submit(jf.library_stats, jf_id): idx
                            for idx, jf_id in id_map
                        }

                        for fut in concurrent.futures.as_completed(
                            future_to_idx, timeout=None
                        ):
                            idx = future_to_idx.get(fut)
                            try:
                                stats = fut.result(timeout=5)
                                flat[idx]["ItemCount"] = (
                                    stats.get("item_count", 0)
                                    if isinstance(stats, dict) and stats.get("ok")
                                    else 0
                                )
                            except Exception:
                                flat[idx]["ItemCount"] = 0
            except Exception:
                for lib in flat:
                    lib_id = lib.get("Id")
                    if lib_id:
                        stats = jf.library_stats(lib_id)
                        if stats.get("ok"):
                            lib["ItemCount"] = stats.get("item_count", 0)

            def _is_media_library(lib: dict) -> bool:
                t = (lib.get("CollectionType") or lib.get("Type") or "")
                t_norm = str(t).strip().lower()
                if not t_norm:
                    return False
                return any(k in t_norm for k in ("movies", "tvshows"))

            filtered = [l for l in flat if _is_media_library(l)]
            result["data"] = filtered

            try:
                from services.mappers import map_libraries
                mapped = map_libraries(filtered)
                repo.upsert_libraries(mapped)
            except Exception:
                pass

        return jsonify(result), 200

    @app.get("/api/analytics/users")
    def api_analytics_users() -> Response:
        """
        Retrieve all users from repository.
        """
        return jsonify({"ok": True, "data": repo.list_users()}), 200

    @app.get("/api/analytics/libraries")
    def api_analytics_libraries() -> Response:
        """
        Retrieve all libraries from repository.
        """
        settings = svc.get()
        
        if not (
            settings.get("jf_host")
            and settings.get("jf_port")
            and settings.get("jf_api_key")
        ):
            return jsonify({
                "ok": True,
                "data": []
            }), 200
        
        try:
            libraries = repo.list_libraries(include_archived=False)

            for lib in libraries:
                jf_id = lib.get("jellyfin_id")
                if not jf_id:
                    lib["item_count"] = 0
                    continue

                t = (lib.get("type") or "").strip().lower()
                if "tvshows" in t:
                    items_res = jf.library_items(jf_id)
                    if items_res.get("ok"):
                        items = items_res.get("data", {}).get("Items", []) or []
                        series = sum(1 for it in items if (it.get("Type") or "").lower() == "series")
                        episodes = sum(1 for it in items if (it.get("Type") or "").lower() == "episode")
                        lib["series_count"] = series
                        lib["episode_count"] = episodes
                        lib["item_count"] = series + episodes
                    else:
                        lib["series_count"] = 0
                        lib["episode_count"] = 0
                        lib["item_count"] = 0
                else:
                    stats = jf.library_stats(jf_id)
                    lib["item_count"] = stats.get("item_count", 0) if stats.get("ok") else 0

            return jsonify({
                "ok": True,
                "data": libraries
            }), 200
        
        except Exception as exc:
            return jsonify({
                "ok": False,
                "message": f"Failed to fetch libraries: {str(exc)}"
            }), 500

    @app.post("/api/analytics/library/<string:jellyfin_id>/tracked")
    def api_analytics_set_tracked(jellyfin_id: str) -> Response:
        """
        Update the tracked flag for a library.
        """
        payload = request.get_json(silent=True) or {}
        tracked = payload.get("tracked", None)
        if not isinstance(tracked, bool):
            return jsonify({
                "ok": False,
                "status": 400,
                "message": "tracked must be boolean"
            }), 200

        updated = repo.set_library_tracked(jellyfin_id, tracked)
        if not updated:
            return jsonify({
                "ok": False,
                "status": 404,
                "message": "Library not found"
            }), 200

        return jsonify({"ok": True, "data": updated}), 200

    @app.post("/api/sync")
    def api_sync() -> Response:
        """
        Trigger a manual sync operation.
        """
        payload = request.get_json(silent=True) or {}
        sync_type = payload.get("type", "full")
        auto_track = bool(payload.get("auto_track", False))

        result = sync.sync_full(auto_track=auto_track)

        return jsonify({
            "ok": result.success,
            "data": result.to_dict()
        }), 200
    
    @app.get("/api/analytics/stats/libraries")
    def api_analytics_stats_libraries() -> Response:
        """
        Retrieve all libraries with their play count statistics.
        """
        try:
            stats = repo.get_library_stats(include_archived=False)
            return jsonify({
                "ok": True,
                "data": stats
            }), 200
        except Exception as exc:
            return jsonify({
                "ok": False,
                "message": f"Failed to fetch library stats: {str(exc)}"
            }), 500

    @app.get("/api/analytics/stats/items")
    def api_analytics_stats_items() -> Response:
        """
        Retrieve the most played items across all libraries.
        """
        try:
            limit = request.args.get("limit", 10, type=int)
            if limit < 1 or limit > 100:
                limit = 10
            
            items = repo.get_top_items_by_plays(limit=limit)
            return jsonify({
                "ok": True,
                "data": items
            }), 200
        except Exception as exc:
            return jsonify({
                "ok": False,
                "message": f"Failed to fetch item stats: {str(exc)}"
            }), 500

    @app.get("/api/analytics/stats/users")
    def api_analytics_stats_users() -> Response:
        """
        Retrieve the most active users by total play count.
        """
        try:
            limit = request.args.get("limit", 10, type=int)
            if limit < 1 or limit > 100:
                limit = 10
            
            users = repo.get_top_users_by_plays(limit=limit)
            return jsonify({
                "ok": True,
                "data": users
            }), 200
        except Exception as exc:
            return jsonify({
                "ok": False,
                "message": f"Failed to fetch user stats: {str(exc)}"
            }), 500
        
    @app.get("/api/analytics/server/sync-progress")
    def api_analytics_server_sync_progress() -> Response:
        """
        Get the current progress of initial activity log sync.
        """
        try:
            # Check if there's an in-progress full activity log sync
            task = repo.get_latest_sync_task()

            if not task or task["result"] != "RUNNING":
                # No sync in progress
                return jsonify({
                    "ok": True,
                    "syncing": False,
                    "processed_events": 0,
                    "total_events": 0
                }), 200

            import json
            log_data = {}
            if task.get("log_json"):
                try:
                    log_data = json.loads(task["log_json"])
                except Exception:
                    pass

            processed = log_data.get("items_synced", 0)
            total = log_data.get("total_events", 1)

            return jsonify({
                "ok": True,
                "syncing": True,
                "processed_events": processed,
                "total_events": total
            }), 200

        except Exception as exc:
            return jsonify({
                "ok": False,
                "message": f"Failed to fetch sync progress: {str(exc)}"
            }), 500

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(
        host="127.0.0.1",
        port=application.config["PORT"]
    )