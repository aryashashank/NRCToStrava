import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Nike Run Club
# ---------------------------------------------------------------------------
NRC_BEARER_TOKEN = os.getenv("NRC_BEARER_TOKEN", "")

NRC_API_BASE = "https://api.nike.com/plus/v3"
NRC_ACTIVITIES_URL = f"{NRC_API_BASE}/activities/before_id/v3/*?limit=30&types=run%2Cjogging&include_deleted=false"
NRC_ACTIVITY_DETAIL_URL = f"{NRC_API_BASE}/activity/{{activity_id}}?metrics=ALL"

# ---------------------------------------------------------------------------
# Strava
# ---------------------------------------------------------------------------
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID", "")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET", "")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN", "")

STRAVA_AUTH_URL = "https://www.strava.com/api/v3/oauth/token"
STRAVA_UPLOAD_URL = "https://www.strava.com/api/v3/uploads"

# ---------------------------------------------------------------------------
# Local paths
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
NRC_JSON_DIR = os.path.join(DATA_DIR, "nrc_json")
GPX_DIR = os.path.join(DATA_DIR, "gpx")

# Ensure directories exist
for d in [DATA_DIR, NRC_JSON_DIR, GPX_DIR]:
    os.makedirs(d, exist_ok=True)


def validate_nrc():
    """Check that the Nike bearer token is configured."""
    if not NRC_BEARER_TOKEN:
        print("ERROR: NRC_BEARER_TOKEN is not set.")
        print("Copy .env.example to .env and fill in your Nike bearer token.")
        sys.exit(1)


def validate_strava():
    """Check that all Strava credentials are configured."""
    missing = []
    if not STRAVA_CLIENT_ID:
        missing.append("STRAVA_CLIENT_ID")
    if not STRAVA_CLIENT_SECRET:
        missing.append("STRAVA_CLIENT_SECRET")
    if not STRAVA_REFRESH_TOKEN:
        missing.append("STRAVA_REFRESH_TOKEN")
    if missing:
        print(f"ERROR: Missing Strava config: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your Strava credentials.")
        sys.exit(1)

