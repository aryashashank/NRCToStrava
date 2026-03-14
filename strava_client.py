"""Strava API client.

Handles OAuth token refresh and GPX file uploads via the Strava V3 API.
Rate limits: 100 requests per 15 minutes, 1000 per day.
"""

import os
import time
import xml.etree.ElementTree as ET
from collections import Counter

import requests

import config

_access_token: str | None = None
_date_counter: Counter = Counter()


def _get_access_token() -> str:
    """Get a fresh Strava access token using the refresh token."""
    global _access_token

    if _access_token:
        return _access_token

    resp = requests.post(
        config.STRAVA_AUTH_URL,
        data={
            "client_id": config.STRAVA_CLIENT_ID,
            "client_secret": config.STRAVA_CLIENT_SECRET,
            "refresh_token": config.STRAVA_REFRESH_TOKEN,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"ERROR: Strava auth failed (HTTP {resp.status_code})")
        print(resp.text)
        raise SystemExit(1)

    data = resp.json()
    _access_token = data["access_token"]
    print(f"  Strava auth OK (token expires in {data.get('expires_in', '?')}s)")
    return _access_token


def _get_activity_date(gpx_path: str) -> str:
    """Extract the activity date (YYYY-MM-DD) from a GPX file's metadata time."""
    try:
        tree = ET.parse(gpx_path)
        root = tree.getroot()
        ns = {"gpx": "http://www.topografix.com/GPX/1/1"}
        time_el = root.find("gpx:metadata/gpx:time", ns)
        if time_el is not None and time_el.text:
            return time_el.text[:10]  # "2021-06-18T..." -> "2021-06-18"
    except Exception:
        pass
    return "unknown"


def _make_activity_name(gpx_path: str) -> str:
    """Generate a name like 'NRC Run 2021-06-18' or 'NRC Run 2021-06-18 (2)' for duplicates."""
    date_str = _get_activity_date(gpx_path)
    _date_counter[date_str] += 1
    count = _date_counter[date_str]
    if count == 1:
        return f"NRC Run {date_str}"
    return f"NRC Run {date_str} ({count})"


def upload_gpx(gpx_path: str, name: str | None = None) -> dict | None:
    """Upload a single GPX file to Strava.

    Returns the upload status dict, or None on failure.
    """
    token = _get_access_token()
    filename = os.path.basename(gpx_path)
    activity_name = name or _make_activity_name(gpx_path)

    with open(gpx_path, "rb") as f:
        resp = requests.post(
            config.STRAVA_UPLOAD_URL,
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (filename, f, "application/gpx+xml")},
            data={
                "data_type": "gpx",
                "activity_type": "run",
                "name": activity_name,
            },
            timeout=60,
        )

    if resp.status_code == 201:
        return resp.json()

    if resp.status_code == 409:
        # Duplicate activity
        print(f"    ↳ duplicate detected, skipping")
        return {"status": "duplicate"}

    if resp.status_code == 429:
        print("    ↳ rate limited — waiting 15 minutes …")
        time.sleep(15 * 60)
        return upload_gpx(gpx_path)  # retry once

    print(f"    ↳ upload failed (HTTP {resp.status_code}): {resp.text[:200]}")
    return None


def check_upload_status(upload_id: int) -> dict:
    """Poll Strava for the processing status of an upload."""
    token = _get_access_token()
    resp = requests.get(
        f"{config.STRAVA_UPLOAD_URL}/{upload_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    return resp.json()


def upload_all_gpx() -> tuple[int, int, int]:
    """Upload every GPX file in the gpx directory to Strava.

    Returns (uploaded, duplicates, failed) counts.
    """
    config.validate_strava()
    _date_counter.clear()

    # Sort GPX files by their activity date so same-day numbering is correct
    gpx_files_unsorted = [f for f in os.listdir(config.GPX_DIR) if f.endswith(".gpx")]
    gpx_files = sorted(
        gpx_files_unsorted,
        key=lambda f: _get_activity_date(os.path.join(config.GPX_DIR, f)),
    )

    if not gpx_files:
        print("No GPX files found. Run the convert step first.")
        return (0, 0, 0)

    uploaded = 0
    duplicates = 0
    failed = 0

    for i, fname in enumerate(gpx_files, 1):
        gpx_path = os.path.join(config.GPX_DIR, fname)
        print(f"  [{i}/{len(gpx_files)}] Uploading {fname} …")

        result = upload_gpx(gpx_path)

        if result is None:
            failed += 1
        elif result.get("status") == "duplicate":
            duplicates += 1
        else:
            uploaded += 1
            upload_id = result.get("id")
            if upload_id:
                print(f"    ↳ queued (upload id: {upload_id})")

        # Respect rate limits: ~6 per minute to stay safe
        time.sleep(10)

    print(f"\nUpload done: {uploaded} uploaded, {duplicates} duplicates, {failed} failed")
    return (uploaded, duplicates, failed)

