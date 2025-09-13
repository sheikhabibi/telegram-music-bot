import os
import yt_dlp
import asyncio
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import json
from datetime import datetime
import time
import pytz

# --- CONFIG ---
from dotenv import load_dotenv

load_dotenv()  # loads values from .env

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
DOWNLOAD_FOLDER = "songs_tele"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# --- Spotify setup ---
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))


# --- Helpers ---
def get_spotify_tracks(url):
    tracks = []
    if "playlist" in url:
        results = sp.playlist_tracks(url)
        while results:
            for item in results['items']:
                track = item['track']
                if track:
                    tracks.append(f"{track['name']} {track['artists'][0]['name']}")
            results = sp.next(results) if results['next'] else None
    elif "track" in url:
        track = sp.track(url)
        tracks.append(f"{track['name']} {track['artists'][0]['name']}")
    return tracks

async def download_song_async(url):
    def download():
        os.makedirs("songs_tele", exist_ok=True)
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'songs_tele/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '0',
            }],
            'quiet': True,
            'noplaylist': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_query = url if "youtube.com" in url or "youtu.be" in url else f"ytsearch1:{url}"
            info = ydl.extract_info(search_query, download=True)
            if 'entries' in info:
                info = info['entries'][0]
            filename = ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")
            return filename

    return await asyncio.to_thread(download)
    



# --- Telegram handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 Send me a Spotify or YouTube link and I’ll download the song/playlist!")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if "spotify.com" in url:
        songs = get_spotify_tracks(url)
    elif "youtube.com" in url or "youtu.be" in url:
        songs = [url]
    else:
        await update.message.reply_text("❌ Unsupported link. Send me a Spotify or YouTube link.")
        return

    # Send initial message
    message = await update.message.reply_text(f"⬇️ Starting {len(songs)} downloads...")

    async def process_song(song):
        await update.message.reply_text(f"⬇️ Downloading: {song}")
        filename = await download_song_async(song)

        if filename:
            drive_link, file_id = upload_to_drive(filename)     #uploading file to drive

            if drive_link and file_id:

                 # 🧹 delete local file after successful upload
                try:
                    os.remove(filename)
                    print(f"Deleted local file: {filename}")
                except Exception as e:
                    print(f"Failed to delete local file {filename}: {e}")


                # Calculate delay for 30 minutes
                delay = 30 * 60
                # Save in JSON for persistent scheduling
                pending = load_pending_deletes()
                pending[file_id] = int(time.time() + delay)
                save_pending_deletes(pending)
    
                # Schedule deletion
                asyncio.create_task(schedule_delete(file_id, delay))

                 # Log the download
                log_download(
                    user_id=update.message.from_user.id,
                    username=update.message.from_user.username or str(update.message.from_user.id),
                    song_name=os.path.basename(filename),
                    drive_link=drive_link
                )
                
                button = InlineKeyboardMarkup([[InlineKeyboardButton("⬇️ Download Song", url=drive_link)]])
                await update.message.reply_text(
                    f"✅ {os.path.basename(filename)} ready!\n⏳ Link expires in 30 minutes",
                    reply_markup=button
                )
            else:
                await update.message.reply_text(f"⚠️ Upload failed for {song}")
        else:
            await update.message.reply_text(f"❌ Could not download {song}")

    # Run all downloads concurrently
    await asyncio.gather(*(process_song(song) for song in songs))

    await message.edit_text(f"✅ All downloads finished!")




# --- Google Drive Setup ---
gauth = GoogleAuth()
gauth.LoadClientConfigFile("client_secrets.json")
gauth.LocalWebserverAuth()  # only first run (opens browser for login)
drive = GoogleDrive(gauth)


async def schedule_delete(file_id, delay=1800):
    """Delete a Drive file after `delay` seconds (default 30 minutes)."""
    await asyncio.sleep(delay)
    try:
        file = drive.CreateFile({'id': file_id})
        file.Delete()
        print(f"Deleted file {file_id} from Drive")
    except Exception as e:
        print(f"Failed to delete file {file_id}: {e}")



def upload_to_drive(file_path, folder_id=None):
    
    try:
        metadata = {'title': os.path.basename(file_path)}
        if folder_id:
            metadata['parents'] = [{'id': folder_id}]
        
        file = drive.CreateFile(metadata)
        file.SetContentFile(file_path)
        file.Upload()
        # Make file shareable
        file.InsertPermission({'type': 'anyone', 'value': 'anyone', 'role': 'reader'})
        
        # Return both the link and the file ID
        return file['alternateLink'], file['id']
    except Exception as e:
        print(f"Drive upload failed: {e}")
        return None, None

# --- logging ---
LOG_FILE = "download_history.json"
IST = pytz.timezone("Asia/Kolkata")

def log_download(user_id, username, song_name, drive_link):
    """Log a download for a user in JSON format."""
    entry = {
        "timestamp": datetime.now(IST).isoformat(),
        "username": username,
        "song": song_name,
        # "drive_link": drive_link
    }

    # Load existing log
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {}

    # Add entry for user
    if str(user_id) not in data:
        data[str(user_id)] = []
    data[str(user_id)].append(entry)

    # Save back
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- deleting drive songs after 30 mins ---
PENDING_DELETE_FILE = "pending_deletes.json"

# Load or initialize pending deletes
def load_pending_deletes():
    if os.path.exists(PENDING_DELETE_FILE):
        with open(PENDING_DELETE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_pending_deletes(data):
    with open(PENDING_DELETE_FILE, "w") as f:
        json.dump(data, f, indent=4)

async def schedule_delete(file_id, delay):
    """Delete a Drive file after `delay` seconds and update pending JSON."""
    await asyncio.sleep(delay)
    try:
        file = drive.CreateFile({'id': file_id})
        file.Delete()
        print(f"Deleted file {file_id} from Drive")
    except Exception as e:
        print(f"Failed to delete file {file_id}: {e}")
    finally:
        # Remove from pending deletes JSON
        pending = load_pending_deletes()
        pending.pop(file_id, None)
        save_pending_deletes(pending)


# --- Main ---
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    async def resume_pending_deletes():
        pending = load_pending_deletes()
        now = int(time.time())
        for file_id, delete_at in pending.items():
            delay = max(0, delete_at - now)
            asyncio.create_task(schedule_delete(file_id, delay))

    # Schedule at startup
    asyncio.get_event_loop().create_task(resume_pending_deletes())

    app.run_polling()

if __name__ == "__main__":
    main()
