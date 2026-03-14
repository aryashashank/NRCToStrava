#!/usr/bin/env python3
"""SyncMyTracks — migrate Nike Run Club activities to Strava.

Usage:
    python main.py              # run full pipeline: fetch → convert → upload
    python main.py fetch        # only fetch NRC activities
    python main.py convert      # only convert NRC JSON → GPX
    python main.py upload       # only upload GPX files to Strava
"""

import sys

from nrc_client import download_all_activities
from gpx_converter import convert_all
from strava_client import upload_all_gpx


def step_fetch():
    print("=" * 60)
    print("STEP 1: Fetching activities from Nike Run Club")
    print("=" * 60)
    paths = download_all_activities()
    print(f"  → {len(paths)} activity files ready\n")
    return paths


def step_convert():
    print("=" * 60)
    print("STEP 2: Converting NRC activities to GPX")
    print("=" * 60)
    gpx_paths = convert_all()
    print(f"  → {len(gpx_paths)} GPX files ready\n")
    return gpx_paths


def step_upload():
    print("=" * 60)
    print("STEP 3: Uploading GPX files to Strava")
    print("=" * 60)
    uploaded, dupes, failed = upload_all_gpx()
    print(f"  → {uploaded} uploaded, {dupes} duplicates, {failed} failed\n")
    return uploaded, dupes, failed


def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║            SyncMyTracks — NRC → Strava                  ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    command = sys.argv[1] if len(sys.argv) > 1 else "all"

    if command == "fetch":
        step_fetch()
    elif command == "convert":
        step_convert()
    elif command == "upload":
        step_upload()
    elif command == "all":
        step_fetch()
        step_convert()
        step_upload()
        print("🏁 All done! Check your Strava account.")
    else:
        print(f"Unknown command: {command}")
        print("Usage: python main.py [fetch|convert|upload|all]")
        sys.exit(1)


if __name__ == "__main__":
    main()

