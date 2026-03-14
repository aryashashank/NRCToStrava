"""Convert NRC activity JSON to GPX format.

GPX (GPS Exchange Format) is a standard XML format that Strava accepts
for activity uploads.  We map NRC's metrics arrays (latitude, longitude,
elevation, heart_rate) into GPX trackpoints.
"""

import json
import os
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

import config


def _get_metric_values(metrics: list[dict], metric_type: str) -> list[dict]:
    """Extract a specific metric's values list from NRC metrics array."""
    for m in metrics:
        if m.get("type") == metric_type:
            return m.get("values", [])
    return []


def _ms_to_iso(epoch_ms: int) -> str:
    """Convert epoch milliseconds to ISO 8601 UTC string."""
    dt = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_gpx_xml(activity: dict) -> str | None:
    """Build a GPX XML string from an NRC activity dict.

    Returns None if the activity has no GPS data.
    """
    metrics = activity.get("metrics", [])
    latitudes = _get_metric_values(metrics, "latitude")
    longitudes = _get_metric_values(metrics, "longitude")

    if not latitudes or not longitudes:
        return None  # no GPS data

    elevations = _get_metric_values(metrics, "elevation")
    heart_rates = _get_metric_values(metrics, "heart_rate")

    # Build lookup dicts keyed by start_epoch_ms for quick matching
    elev_map = {v["start_epoch_ms"]: v["value"] for v in elevations if "start_epoch_ms" in v}
    hr_map = {v["start_epoch_ms"]: v["value"] for v in heart_rates if "start_epoch_ms" in v}

    # GPX root
    gpx = Element("gpx")
    gpx.set("version", "1.1")
    gpx.set("creator", "SyncMyTracks - NRC to Strava")
    gpx.set("xmlns", "http://www.topografix.com/GPX/1/1")
    gpx.set("xmlns:gpxtpx", "http://www.garmin.com/xmlschemas/TrackPointExtension/v1")

    # Metadata
    metadata = SubElement(gpx, "metadata")
    start_ms = activity.get("start_epoch_ms", 0)
    time_el = SubElement(metadata, "time")
    time_el.text = _ms_to_iso(start_ms)

    # Track
    trk = SubElement(gpx, "trk")
    name_el = SubElement(trk, "name")
    tags = activity.get("tags", {})
    name_el.text = tags.get("com.nike.name", f"NRC Run {_ms_to_iso(start_ms)}")

    type_el = SubElement(trk, "type")
    type_el.text = "running"

    trkseg = SubElement(trk, "trkseg")

    # Match lat/lon by index (they share the same sample count)
    count = min(len(latitudes), len(longitudes))
    for i in range(count):
        lat_entry = latitudes[i]
        lon_entry = longitudes[i]

        lat = lat_entry.get("value")
        lon = lon_entry.get("value")
        ts = lat_entry.get("start_epoch_ms")

        if lat is None or lon is None:
            continue

        trkpt = SubElement(trkseg, "trkpt")
        trkpt.set("lat", f"{lat:.7f}")
        trkpt.set("lon", f"{lon:.7f}")

        if ts is not None:
            t = SubElement(trkpt, "time")
            t.text = _ms_to_iso(ts)

        # Elevation
        if ts in elev_map:
            ele = SubElement(trkpt, "ele")
            ele.text = f"{elev_map[ts]:.1f}"

        # Heart rate (GPX extension)
        if ts in hr_map:
            extensions = SubElement(trkpt, "extensions")
            tpx = SubElement(extensions, "gpxtpx:TrackPointExtension")
            hr = SubElement(tpx, "gpxtpx:hr")
            hr.text = str(int(hr_map[ts]))

    # Pretty-print
    raw = tostring(gpx, encoding="unicode")
    pretty = parseString(raw).toprettyxml(indent="  ")
    # Remove extra XML declaration added by minidom
    lines = pretty.split("\n")
    if lines[0].startswith("<?xml"):
        lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    return "\n".join(lines)


def convert_activity(json_path: str) -> str | None:
    """Convert a single NRC JSON file to GPX.

    Returns the GPX file path, or None if the activity has no GPS data.
    """
    with open(json_path) as f:
        activity = json.load(f)

    gpx_xml = _build_gpx_xml(activity)
    if gpx_xml is None:
        return None

    activity_id = activity.get("id", os.path.basename(json_path).replace(".json", ""))
    gpx_path = os.path.join(config.GPX_DIR, f"{activity_id}.gpx")

    with open(gpx_path, "w") as f:
        f.write(gpx_xml)

    return gpx_path


def convert_all() -> list[str]:
    """Convert all downloaded NRC JSON files to GPX.

    Skips activities that already have a GPX file or lack GPS data.
    Returns list of GPX file paths.
    """
    json_files = sorted(
        f for f in os.listdir(config.NRC_JSON_DIR) if f.endswith(".json")
    )

    if not json_files:
        print("No NRC JSON files found. Run the fetch step first.")
        return []

    gpx_paths: list[str] = []
    skipped_no_gps = 0
    skipped_exists = 0

    for i, fname in enumerate(json_files, 1):
        activity_id = fname.replace(".json", "")
        gpx_dest = os.path.join(config.GPX_DIR, f"{activity_id}.gpx")

        if os.path.exists(gpx_dest):
            skipped_exists += 1
            gpx_paths.append(gpx_dest)
            continue

        json_path = os.path.join(config.NRC_JSON_DIR, fname)
        result = convert_activity(json_path)

        if result:
            print(f"  [{i}/{len(json_files)}] Converted {activity_id}")
            gpx_paths.append(result)
        else:
            skipped_no_gps += 1
            print(f"  [{i}/{len(json_files)}] {activity_id} — no GPS data, skipped")

    print(f"\nConversion done: {len(gpx_paths)} GPX files")
    if skipped_exists:
        print(f"  {skipped_exists} already existed (skipped)")
    if skipped_no_gps:
        print(f"  {skipped_no_gps} had no GPS data (skipped)")

    return gpx_paths

