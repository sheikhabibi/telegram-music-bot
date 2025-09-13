# 🎵 Telegram Music Downloader Bot (Vibe Coding)

A Telegram bot that downloads songs from **Spotify tracks/playlists** or **YouTube videos/playlists**, converts them to MP3, uploads them to Google Drive, and sends you a temporary download link.

## ✨ Features
- Spotify & YouTube link handling
- MP3 extraction with yt-dlp (320kbps)
- Google Drive upload with 30-min auto-expiry
- JSON-based history logging per user
- Parallel downloads for playlists


---


## 🔑 Required API Keys and Secrets

Before running the bot, you need API keys from the following platforms:

1. **Telegram Bot Token**
   - Create a bot via [BotFather](https://t.me/BotFather) on Telegram.
   - Save the token.

2. **Spotify API**
   - Create a developer account at [Spotify Developer](https://developer.spotify.com/).
   - Create an app and get:
        - `SPOTIFY_CLIENT_ID`
        - `SPOTIFY_CLIENT_SECRET`

3. **Google Drive API**
   - Go to [Google Cloud Console](https://console.cloud.google.com/).
   - Enable Drive API and create OAuth client credentials.
   - Download `client_secrets.json`.


---


## 🔐 Add secrets
### 1. create a .env file in the project root with:
```
TELEGRAM_TOKEN=your_telegram_token
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
```
### 2. Add Google Drive credentials
Place the downloaded `client_secrets.json` in the project root.

### 3. Run the bot
```
python tele_bot.py
```

## 🚀 Setup

### 1. Clone Repo
```bash
git clone https://github.com/sheikhabibi/telegram-music-bot.git
cd telegram-music-bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

## File/Folder Summary
| File/Folder             | Purpose                              | Notes                      |
| ----------------------- | ------------------------------------ | -------------------------- |
| `tele_bot.py`           | Main bot code                        | Must be present            |
| `.env`                  | Stores Telegram & Spotify API keys   | User must create locally   |
| `client_secrets.json`   | Google Drive OAuth credentials       | User must create locally   |
| `songs_tele/`           | Download folder for MP3s             | Bot will create if missing |
| `download_history.json` | Logs user downloads                  | Auto-generated             |
| `pending_deletes.json`  | Tracks files to delete after 30 mins | Auto-generated             |
