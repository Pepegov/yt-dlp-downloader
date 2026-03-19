import yt_dlp
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from mutagen.easyid3 import EasyID3
import re

from genius_lyrics import GeniusLyricsFetcher
from lrc_lyrics import LRCLyricsFetcher


def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "-", name).strip()


class TrackDownloader:
    def __init__(
        self,
        download_folder="downloads",
        max_workers=4,
        genius_lyrics_fetcher: GeniusLyricsFetcher | None = None
    ):
        self.download_folder = Path(download_folder)
        self.download_folder.mkdir(exist_ok=True)
        self.max_workers = max_workers

        self.genius_lyrics_fetcher = genius_lyrics_fetcher
        self.lrc_lyrics_fetcher = LRCLyricsFetcher()

    def _fix_tags(self, file_path, artist, title, album=None, track_number=None, total_tracks=None, year=None):
        try:
            audio = EasyID3(file_path)
        except Exception:
            audio = EasyID3()

        audio["artist"] = artist
        audio["albumartist"] = artist
        audio["title"] = title

        # Для тега album используем оригинальный album или title
        album_tag = album if album is not None else title
        audio["album"] = album_tag

        # tracknumber
        if track_number is not None:
            if total_tracks is not None:
                audio["tracknumber"] = f"{track_number}/{total_tracks}"
            else:
                audio["tracknumber"] = str(track_number)
        elif album is None:  # проверяем оригинальный album, а не изменённый
            audio["tracknumber"] = "1/1"

        if year:
            audio["date"] = year

        audio.save(file_path)

    # -------------------------
    # DOWNLOAD
    # -------------------------
    def _download_single(self, url, artist_folder, album=None, track_index=None, total_tracks=1):

        if album:
            album = sanitize_filename(album)
            folder = artist_folder / album
            folder.mkdir(parents=True, exist_ok=True)
        else:
            folder = artist_folder

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(folder / "%(id)s.%(ext)s"),
            "embed_metadata": True,
            "writethumbnail": True,
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
                {"key": "FFmpegMetadata"},
                {"key": "EmbedThumbnail"},
            ],
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        video_id = info.get("id")
        temp_file = folder / f"{video_id}.mp3"

        artist_name = info.get("uploader") or artist_folder.name
        title = info.get("title", "Unknown Title")
        year = info.get("release_year") or info.get("upload_date", "")[:4]

        if track_index:
            new_name = f"{track_index:02d} - {artist_name} - {title}.mp3"
        else:
            new_name = f"{artist_name} - {title}.mp3"

        new_name = sanitize_filename(new_name)
        new_path = folder / new_name

        if temp_file != new_path:
            counter = 1
            base = new_path.stem
            while new_path.exists():
                new_path = folder / f"{base}_{counter}.mp3"
                counter += 1
            temp_file.rename(new_path)

        self._fix_tags(
            new_path,
            artist=artist_folder.name,
            title=title,
            album=album,
            track_number=track_index,
            year=year,
            total_tracks=total_tracks
        )

        # 🎵 lyrics (если включены)
        if (self.genius_lyrics_fetcher is not None):
            self.genius_lyrics_fetcher._add_unsync_lyrics(new_path, artist_folder.name, title)
        if (self.lrc_lyrics_fetcher is not None):
            self.lrc_lyrics_fetcher.add_lyrics(new_path, artist_folder.name, title)

    def download(self, url):
        with yt_dlp.YoutubeDL({"extract_flat": True}) as ydl:
            info = ydl.extract_info(url, download=False)

        if "entries" in info:
            artist = info.get("uploader") or "Unknown Artist"
            album = info.get("title")
            entries = info["entries"]
        else:
            artist = info.get("uploader") or "Unknown Artist"
            album = info.get("album")
            entries = [info]

        artist_folder = self.download_folder / artist
        artist_folder.mkdir(exist_ok=True)

        if len(entries) == 1:
            self._download_single(url, artist_folder, album)
        else:
            total = len(entries)
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for i, entry in enumerate(entries, start=1):
                    track_url = entry.get("webpage_url") or entry.get("url")
                    if not track_url:
                        continue
                    futures.append(executor.submit(
                        self._download_single,
                        track_url,
                        artist_folder,
                        album,
                        i,
                        total 
                    ))
                for f in futures:
                    f.result()