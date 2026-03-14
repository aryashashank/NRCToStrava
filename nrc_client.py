"""Nike Run Club API client.

Uses Nike's undocumented sport API to fetch all run activities and their
detailed metrics (GPS, heart rate, elevation, pace, etc.).
"""

import json
import os
import time

import requests

import config


def _headers():
    return {
        "Authorization": f"Bearer {config.NRC_BEARER_TOKEN}",
        "Content-Type": "application/json",
    }


def fetch_activities() -> list[dict]:
    """Fetch all activities by paginating through the Nike API.

    Nike returns activities in pages using ``before_id`` pagination.
    Each response contains a list of activities and a ``paging`` object
    with a ``before_id`` for the next page.

    Returns full activity summary dicts (not just IDs) so we can filter
    out non-run activities (e.g. NTC training).
    """
    all_activities: list[dict] = []
    url = config.NRC_ACTIVITIES_URL
    page = 1

    while url:
        print(f"  Fetching activity list page {page} …")
        resp = requests.get(url, headers=_headers(), timeout=30)

        if resp.status_code == 401:
            print("ERROR: Nike returned 401 – your bearer token is invalid or expired.")
            print("Get a fresh token from nike.com DevTools and update .env")
            break

        resp.raise_for_status()
        data = resp.json()

        activities = data.get("activities", [])
        for act in activities:
            # Skip NTC (Nike Training Club) records — only keep runs
            app_id = act.get("app_id", "")
            if app_id in ("com.nike.ntc.brand.ios", "com.nike.ntc.brand.droid"):
                print(f"    Skipping NTC record {act.get('id')}")
                continue
            all_activities.append(act)

        # Nike pagination: look for before_id to get older activities
        paging = data.get("paging", {})
        before_id = paging.get("before_id")

        if before_id:
            url = f"{config.NRC_API_BASE}/activities/before_id/v3/{before_id}?limit=30&types=run%2Cjogging&include_deleted=false"
        else:
            url = None  # no more pages

        page += 1
        time.sleep(0.5)  # be polite

    print(f"  Found {len(all_activities)} run activities total.")
    return all_activities


def fetch_activity_detail(activity_id: str) -> dict | None:
    """Fetch full detail (including metrics) for a single activity."""
    url = config.NRC_ACTIVITY_DETAIL_URL.format(activity_id=activity_id)
    resp = requests.get(url, headers=_headers(), timeout=30)

    if resp.status_code == 401:
        print("ERROR: Bearer token expired mid-run. Update .env and retry.")
        return None

    if resp.status_code != 200:
        print(f"  WARNING: Could not fetch activity {activity_id} (HTTP {resp.status_code})")
        return None

    return resp.json()


def save_activity_json(activity_id: str, data: dict) -> str:
    """Persist raw NRC JSON to disk for debugging / re-processing."""
    path = os.path.join(config.NRC_JSON_DIR, f"{activity_id}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def download_all_activities() -> list[str]:
    """Download every NRC activity's full detail to disk.

    Returns a list of file paths written.
    """
    config.validate_nrc()

    activities = fetch_activities()
    if not activities:
        print("No activities found.")
        return []

    paths: list[str] = []
    for i, act in enumerate(activities, 1):
        act_id = act.get("id")
        if not act_id:
            continue

        dest = os.path.join(config.NRC_JSON_DIR, f"{act_id}.json")
        if os.path.exists(dest):
            print(f"  [{i}/{len(activities)}] {act_id} — already downloaded, skipping")
            paths.append(dest)
            continue

        print(f"  [{i}/{len(activities)}] Fetching {act_id} …")
        detail = fetch_activity_detail(act_id)
        if detail:
            path = save_activity_json(act_id, detail)
            paths.append(path)
        time.sleep(0.5)

    print(f"Downloaded {len(paths)} activities to {config.NRC_JSON_DIR}")
    return paths

