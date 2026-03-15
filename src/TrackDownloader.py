import yt_dlp
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from mutagen.easyid3 import EasyID3
import re

def sanitize_filename(name):
    """Удаляет недопустимые для файловой системы символы."""
    return re.sub(r'[\\/*?:"<>|]', "", name)

class TrackDownloader:
    def __init__(self, download_folder="downloads", max_workers=4):
        self.download_folder = Path(download_folder)
        self.download_folder.mkdir(exist_ok=True)
        self.max_workers = max_workers

    def _fix_tags(self, file_path, artist, album=None, track_number=None):
        """Прописывает ID3-теги, включая albumartist."""
        try:
            audio = EasyID3(file_path)
        except Exception:
            audio = EasyID3()
        audio["artist"] = artist
        audio["albumartist"] = artist          # важно для группировки альбомов
        if album:
            audio["album"] = album
        if track_number is not None:
            audio["tracknumber"] = str(track_number)
        audio.save(file_path)

    def _download_single(self, url, artist_folder, album=None, track_index=None):
        """Скачивает один трек, используя id видео как временное имя."""
        # Папка назначения
        if album:
            folder = artist_folder / album
            folder.mkdir(exist_ok=True)
        else:
            folder = artist_folder

        # Временное имя на основе id видео
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
        if not video_id:
            print(f"Не удалось получить ID видео для {url}")
            return

        # Ищем временный mp3-файл
        temp_file = folder / f"{video_id}.mp3"
        if not temp_file.exists():
            candidates = list(folder.glob(f"{video_id}.*"))
            if candidates:
                temp_file = candidates[0]
            else:
                print(f"Файл для {video_id} не найден")
                return

        # Данные для имени файла
        artist_name = info.get("uploader") or artist_folder.name
        title = info.get("title", "Unknown Title")

        # Желаемое имя
        if track_index is not None:
            new_name = f"{track_index:02d} - {artist_name} - {title}.mp3"
        else:
            new_name = f"{artist_name} - {title}.mp3"

        new_name = sanitize_filename(new_name)
        new_path = folder / new_name

        # Переименование, если имя не совпадает (с защитой от дубликатов)
        if temp_file != new_path:
            counter = 1
            base = new_path.stem
            while new_path.exists():
                new_path = folder / f"{base}_{counter}.mp3"
                counter += 1
            temp_file.rename(new_path)

        # Прописываем теги
        self._fix_tags(new_path, artist=artist_folder.name, album=album, track_number=track_index)

    def download(self, url):
        """Основной метод: загружает трек, альбом или плейлист."""
        # Быстрое получение информации (без скачивания)
        with yt_dlp.YoutubeDL({"extract_flat": True}) as ydl:
            info = ydl.extract_info(url, download=False)

        # Определяем тип контента
        if "entries" in info:
            # Плейлист / альбом
            artist = info.get("uploader") or "Unknown Artist"
            album = info.get("title")
            entries = info["entries"]
        else:
            # Одиночный трек
            artist = info.get("uploader") or "Unknown Artist"
            album = info.get("album")
            entries = [info]

        artist_folder = self.download_folder / artist
        artist_folder.mkdir(exist_ok=True)

        if len(entries) == 1 and "url" in entries[0]:
            # Одиночный трек
            track_url = entries[0].get("webpage_url") or entries[0].get("url") or url
            self._download_single(track_url, artist_folder, album)
        else:
            # Множество треков
            print(f"Найдено {len(entries)} треков у исполнителя '{artist}'"
                  f"{' в альбоме ' + album if album else ''}. Начинаю скачивание...")

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for i, entry in enumerate(entries, start=1):
                    track_url = entry.get("webpage_url") or entry.get("url")
                    if not track_url:
                        continue
                    idx = entry.get("playlist_index", i)
                    futures.append(executor.submit(
                        self._download_single, track_url, artist_folder, album, idx))
                for f in futures:
                    f.result()   # чтобы увидеть возможные ошибки