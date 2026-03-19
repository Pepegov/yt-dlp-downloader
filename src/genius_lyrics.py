import requests
from bs4 import BeautifulSoup
import re
import html
import unicodedata
from mutagen.id3 import ID3, USLT, ID3NoHeaderError


class GeniusLyricsFetcher:
    API_BASE = "https://api.genius.com"
    GENIUS_BASE = "https://genius.com"

    def __init__(self, token: str, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "User-Agent": "LyricsFetcher/1.0",
        })

    def _normalize(self, text: str) -> str:
        text = unicodedata.normalize("NFKD", text or "")
        text = "".join(c for c in text if not unicodedata.combining(c))
        text = text.lower()
        return re.sub(r"[^a-z0-9]+", " ", text).strip()

    def _search(self, artist: str, title: str):
        r = self.session.get(
            f"{self.API_BASE}/search",
            params={"q": f"{artist} {title}"},
            timeout=self.timeout
        )
        r.raise_for_status()
        return r.json()["response"]["hits"]

    def _pick_best(self, hits, artist: str, title: str):
        artist_n = self._normalize(artist)
        title_n = self._normalize(title)

        best = None
        best_score = -1

        for h in hits:
            r = h["result"]

            song_artist = self._normalize(r["primary_artist"]["name"])
            song_title = self._normalize(r["title"])

            score = 0
            if artist_n in song_artist:
                score += 3
            if title_n == song_title:
                score += 5
            elif title_n in song_title:
                score += 3

            if score > best_score:
                best_score = score
                best = r

        return best

    def _scrape_lyrics(self, url: str) -> str:
        page = self.session.get(url, timeout=self.timeout)
        page.raise_for_status()

        soup = BeautifulSoup(page.text, "html.parser")
        containers = soup.select('div[data-lyrics-container="true"]')

        lyrics = []
        for c in containers:
            lyrics.append(c.get_text("\n", strip=True))

        text = "\n\n".join(lyrics)
        text = html.unescape(text)

        return re.sub(r"\n{3,}", "\n\n", text).strip()

    
    def get_lyrics(self, artist: str, title: str) -> str | None:
        hits = self._search(artist, title)
        if not hits:
            return None

        song = self._pick_best(hits, artist, title)
        if not song:
            return None

        url = f"{self.GENIUS_BASE}{song['path']}"
        return self._scrape_lyrics(url)
    
    def _add_unsync_lyrics(self, file_path, artist, title):
        try:
            lyrics = self.get_lyrics(artist, title)
            if not lyrics:
                print(f"[GENIUS LYRICS] Not found: {artist} - {title}")
                return

            try:
                tags = ID3(file_path)
            except ID3NoHeaderError:
                tags = ID3()

            tags.delall("USLT")
            tags.add(USLT(
                encoding=3,
                lang="eng",
                desc="Lyrics",
                text=lyrics
            ))

            tags.save(file_path)

            print(f"[GENIUS LYRICS] Added: {artist} - {title}")

        except Exception as e:
            print(f"[GENIUS LYRICS ERROR] {artist} - {title}: {e}")
