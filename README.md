# NRCToStrava

Migrate your **Nike Run Club** activity history to **Strava** — before Nike shuts it down for good.

NRCToStrava downloads all your NRC runs via Nike's API, converts them to GPX files, and uploads them to Strava with full GPS tracks, elevation, and heart rate data preserved.

## How It Works

```
Nike Run Club API → JSON → GPX → Strava Upload API
```

The pipeline has three steps, each resumable and idempotent:

1. **Fetch** — Downloads all your NRC runs as JSON files
2. **Convert** — Transforms JSON into GPX format (GPS Exchange Format)
3. **Upload** — Pushes GPX files to your Strava account

Activities without GPS data (treadmill/manual entries) are automatically skipped during conversion.

## Prerequisites

- Python 3.10+
- A Nike account with run history
- A Strava account with an [API application](https://www.strava.com/settings/api)

## Setup

### 1. Clone and install

```bash
git clone https://github.com/aryashashank/NRCToStrava.git
cd NRCToStrava
pip install -r requirements.txt
```

### 2. Get your Nike bearer token

> ⚠️ Nike tokens expire in ~1 hour. Don't close your nike.com tab until the fetch completes.

1. Go to [nike.com](https://www.nike.com) and **log in**
2. Open DevTools (`F12`) → **Application** tab → **Local Storage**
3. Click on `https://www.nike.com`
4. Find the key starting with `oidc.user:https://accounts.nike.com:...`
5. Copy the `access_token` value from the JSON (starts with `eyJ...`)

### 3. Get your Strava credentials

#### Create a Strava API application

1. Go to [strava.com/settings/api](https://www.strava.com/settings/api)
2. Fill in the form:
   - **Application Name**: anything (e.g. `NRCToStrava`)
   - **Category**: choose any
   - **Website**: `http://localhost`
   - **Authorization Callback Domain**: `localhost`
3. Click **Create**
4. You'll see your **Client ID** and **Client Secret** on the next page — save both

#### Authorize with write access

By default, Strava apps only get `read` scope. To upload activities, you need to explicitly request `activity:write` via the OAuth flow:

1. Open this URL in your browser (replace `YOUR_CLIENT_ID` with your actual Client ID):
   ```
   https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&scope=read_all,activity:write,activity:read_all&approval_prompt=force
   ```
2. Strava will ask you to authorize the app — make sure the permissions listed include **uploading activities**, then click **Authorize**
3. You'll be redirected to a URL like:
   ```
   http://localhost/?state=&code=AUTHORIZATION_CODE&scope=read,activity:write,activity:read_all,read_all
   ```
   The page won't load (that's expected). Copy the `code` value from the URL bar — it's the part between `code=` and `&scope=`

4. **Immediately** exchange the code for a refresh token (codes expire in minutes):
   ```bash
   curl -X POST https://www.strava.com/api/v3/oauth/token \
     -d client_id=YOUR_CLIENT_ID \
     -d client_secret=YOUR_CLIENT_SECRET \
     -d code=AUTHORIZATION_CODE \
     -d grant_type=authorization_code
   ```
5. The response will contain your `refresh_token` — save it. The script uses this to automatically obtain fresh access tokens, so you only need to do this once

### 4. Configure environment

```bash
cp .env.example .env
```

Fill in your `.env`:

```env
NRC_BEARER_TOKEN=eyJ...
STRAVA_CLIENT_ID=12345
STRAVA_CLIENT_SECRET=abc123...
STRAVA_REFRESH_TOKEN=def456...
```

## Usage

```bash
# Run the full pipeline (fetch → convert → upload)
python main.py

# Or run individual steps
python main.py fetch      # Download NRC activities to data/nrc_json/
python main.py convert    # Convert JSON to GPX in data/gpx/
python main.py upload     # Upload GPX files to Strava
```

Each step is **resumable** — if interrupted, re-running the same command skips already-processed files.

## Rate Limits

- **Nike API**: No known hard limits, but the token expires in ~1 hour
- **Strava API**: 100 uploads per 15 minutes, 1,000 per day. The script adds a 10-second delay between uploads and automatically waits on rate limit errors

## Project Structure

```
NRCToStrava/
├── main.py              # CLI entry point
├── nrc_client.py        # Nike Run Club API client
├── gpx_converter.py     # NRC JSON → GPX converter
├── strava_client.py     # Strava OAuth + upload client
├── config.py            # Configuration and env loading
├── requirements.txt     # Python dependencies
├── .env.example         # Template for credentials
└── data/
    ├── nrc_json/        # Downloaded NRC activity files
    └── gpx/             # Converted GPX files
```

## GPX Data Mapping

| NRC Metric   | GPX Element                          |
|-------------|--------------------------------------|
| Latitude    | `<trkpt lat="...">`                  |
| Longitude   | `<trkpt lon="...">`                  |
| Elevation   | `<ele>`                              |
| Heart Rate  | `<gpxtpx:hr>` (Garmin extension)     |
| Timestamps  | `<time>`                             |
| Run Name    | `<name>` (from Nike tags)            |

## License

MIT