# 🎬 AI Faceless Automation

Fully automated YouTube Shorts generator. Provide a topic → get a ready-to-upload video with SEO metadata, thumbnail, and voiceover. **100% free tools.**

## What It Does

```
Topic → Gemini Pro Script → edge-tts Voice → Pexels Video → Subtitles → Final MP4
                          → SEO Metadata (title, description, tags)
                          → Thumbnail (1280×720)
                          → Google Sheets Log
```

## Quick Start (3 Steps)

### 1. Install dependencies

```bash
cd AI_Faceless_Automation
pip install -r requirements.txt
```

You also need **FFmpeg** installed:
- Download from https://ffmpeg.org/download.html
- Add to your system PATH

### 2. Add your API keys

Create a local `.env` file from `.env.example` and add your keys there:

```bash
copy .env.example .env
```

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
PEXELS_API_KEY=YOUR_PEXELS_KEY
GROQ_API_KEY=YOUR_GROQ_KEY
```

You can still use `config/settings.json` for non-secret settings like resolution, FPS, subtitles, and voice options.

Get a free Gemini key at: https://aistudio.google.com/apikey

### 3. Generate your first video!

```bash
python scripts/main.py "5 mind-blowing facts about the ocean"
```

Your video will be saved in `output/<topic>_<timestamp>/`:
- `final.mp4` — ready to upload
- `thumbnail.png` — YouTube thumbnail
- `metadata.json` — title, description, tags
- `script.txt` — narration script

## Command Line Options

```bash
# Basic usage
python scripts/main.py "your topic here"

# Skip subtitles
python scripts/main.py "your topic" --no-subs

# Override voice
python scripts/main.py "your topic" --voice en-GB-RyanNeural

# Skip Google Sheets logging
python scripts/main.py "your topic" --no-sheet
```

## Available Voices

Voice is auto-selected based on script mood:

| Mood | Voice | Style |
|------|-------|-------|
| Informative | en-US-GuyNeural | Authoritative, clear |
| Motivational | en-US-ChristopherNeural | Deep, inspiring |
| Dramatic | en-GB-RyanNeural | British, suspenseful |
| Fun | en-US-JennyNeural | Friendly, upbeat |
| Tech | en-US-DavisNeural | Professional, modern |
| Storytelling | en-AU-WilliamNeural | Warm, narrative |

## Optional: Pexels Stock Footage

By default, videos use animated gradient backgrounds. For **real stock footage**:

1. Get a free API key at https://www.pexels.com/api/
2. Add it to `.env` as `PEXELS_API_KEY=YOUR_PEXELS_KEY`

## Optional: Google Sheets Tracking

Log every video's metadata to a Google Sheet:

### Setup (one-time, ~5 minutes)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to **Credentials** → **Create Service Account**
5. Download the JSON key → save as `config/credentials.json`
6. Create a new Google Sheet
7. Share the sheet with the service account email (found in credentials.json → `client_email`)
8. Copy the Sheet ID from the URL: `https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`
9. Add the Sheet ID to `.env` and enable logging:

```env
GOOGLE_SHEETS_ENABLED=true
GOOGLE_SHEETS_CREDENTIALS_FILE=config/credentials.json
GOOGLE_SHEETS_SHEET_ID=YOUR_SHEET_ID
GOOGLE_SHEETS_SHEET_TITLE=AI Faceless Video Log
GOOGLE_SHEETS_WORKSHEET_NAME=Videos
GOOGLE_SHEETS_TARGET_EMAIL=rohitsantra8@gmail.com
GOOGLE_DRIVE_ENABLED=true
GOOGLE_DRIVE_FOLDER_NAME=AI Faceless Automation
GOOGLE_DRIVE_FOLDER_ID=
GOOGLE_DRIVE_UPLOAD_THUMBNAIL=true
GOOGLE_DRIVE_UPLOAD_VIDEO=true
GOOGLE_DRIVE_MAKE_PUBLIC=true
```

If `GOOGLE_SHEETS_SHEET_ID` is left blank, the app now tries to create a spreadsheet automatically with `GOOGLE_SHEETS_SHEET_TITLE`, then shares it with `GOOGLE_SHEETS_TARGET_EMAIL`.
Generated thumbnails and final videos can also be uploaded to Google Drive automatically so the sheet can store a public thumbnail preview and Drive links.
If the service account cannot create its own Drive folder because of quota/ownership limits, create a folder in your own Google Drive, share it with the service-account email, and set `GOOGLE_DRIVE_FOLDER_ID` to that folder ID.

## Personal Drive Uploads (OAuth)

If you want thumbnails and final videos to upload directly into your own Google Drive automatically, switch from service-account auth to user OAuth:

1. In Google Cloud, create an `OAuth client ID` for a `Desktop app`
2. Download the client JSON
3. Save it as `config/oauth_client_secret.json`
4. Set:

```env
GOOGLE_AUTH_MODE=oauth_user
GOOGLE_OAUTH_CLIENT_SECRETS_FILE=config/oauth_client_secret.json
GOOGLE_OAUTH_TOKEN_FILE=config/oauth_token.json
```

5. Run:

```bash
python scripts/authorize_google_oauth.py
```

6. Sign in with your Google account in the browser and approve access once

After that, the app will reuse `config/oauth_token.json` and can upload thumbnails and videos into your personal Drive folder automatically.

### Sheet Columns

| # | Column | Description |
|---|--------|-------------|
| 1 | Date | Generation timestamp |
| 2 | Topic | Input topic |
| 3 | Video Title | SEO-optimized title |
| 4 | Description | YouTube description |
| 5 | Tags | Comma-separated tags |
| 6 | Hashtags | Including #Shorts |
| 7 | Category | YouTube category |
| 8 | Vibe | Selected video category |
| 9 | Voice Label | UI voice preset label |
| 10 | Voice ID | edge-tts voice name |
| 11 | Voice Rate | Applied narration speed |
| 12 | Requested Duration | Requested runtime in seconds |
| 13 | Final Duration | Final rendered runtime |
| 14 | Visual Source | Pexels or local |
| 15 | Visual Query | Footage search terms |
| 16 | Thumbnail Text | Generated text used on thumbnail |
| 17 | Thumbnail Path | Local file path |
| 18 | Thumbnail Image | Auto-embeds only when a public thumbnail URL exists |
| 19 | Script | Full narration text |
| 20 | Video Path | Local file path |
| 21 | Upload Status | Pending / Uploaded |

## Project Structure

```
AI_Faceless_Automation/
├── config/
│   ├── settings.json          ← All configuration
│   └── credentials.json       ← Google Sheets (optional)
├── scripts/
│   ├── main.py                ← Run this!
│   ├── script_generator.py    ← Gemini Pro script writing
│   ├── seo_generator.py       ← SEO metadata generation
│   ├── voice_generator.py     ← edge-tts voiceover
│   ├── video_generator.py     ← Pexels / local video
│   ├── subtitle_generator.py  ← Burned-in captions
│   ├── thumbnail_generator.py ← YouTube thumbnails
│   ├── video_merger.py        ← Final assembly
│   └── sheets_logger.py       ← Google Sheets logging
├── output/                    ← Generated videos go here
├── temp/                      ← Temporary files
├── requirements.txt
└── README.md
```

## Configuration

Settings are loaded from `config/settings.json`, then secret values in `.env` override the JSON values. Keep local secrets out of GitHub by using `.env`.

Key options:

| Setting | Default | Description |
|---------|---------|-------------|
| `gemini.api_key` | `""` | **Required.** Your Gemini API key |
| `gemini.model` | `gemini-2.0-flash` | Gemini model to use |
| `pexels.api_key` | `""` | Optional. Pexels API key for stock footage |
| `video.max_duration_seconds` | `40` | Max video duration |
| `video.fps` | `30` | Frames per second |
| `subtitles.enabled` | `true` | Burn subtitles into video |
| `subtitles.font_size` | `65` | Subtitle text size |
| `subtitles.words_per_group` | `3` | Words shown at once |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Gemini API key required` | Add your key to `.env` as `GEMINI_API_KEY` |
| `FFmpeg not found` | Install FFmpeg and add to PATH |
| `edge-tts failed` | Check internet connection (gTTS fallback will try automatically) |
| `No Pexels results` | Video falls back to gradient backgrounds automatically |
| Subtitles look wrong | Adjust `subtitles.font_size` and `subtitles.words_per_group` in settings |
