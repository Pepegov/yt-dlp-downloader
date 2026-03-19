import requests
import re
from mutagen.id3 import ID3, SYLT, USLT, ID3NoHeaderError

class LRCLyricsFetcher:
    """
    Класс для получения синхронизированных (LRC) и обычных текстов песен
    с сервиса lrclib.net и их добавления в ID3-теги (SYLT и USLT) аудиофайлов.
    """

    BASE_URL = "https://lrclib.net/api/get"

    def fetch_lyrics_data(self, artist: str, title: str) -> dict | None:
        """
        Запрашивает у API полные данные о тексте песни.

        :param artist: имя исполнителя
        :param title: название трека
        :return: словарь с данными ответа или None, если не найдено/ошибка
        """
        try:
            response = requests.get(
                self.BASE_URL,
                params={"artist_name": artist, "track_name": title},
                timeout=10
            )
            if response.status_code != 200:
                return None
            return response.json()
        except Exception:
            return None

    def _parse_lrc(self, lrc_text: str) -> list[tuple[str, int]]:
        """
        Преобразует LRC-текст в список кортежей (текст, время_в_мс) для SYLT-тега.

        :param lrc_text: исходный LRC-текст (многострочный)
        :return: список кортежей вида (текст, миллисекунды)
        """
        lines = []
        pattern = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)")

        for line in lrc_text.splitlines():
            match = pattern.match(line)
            if not match:
                continue

            minutes = int(match.group(1))
            seconds = float(match.group(2))
            text = match.group(3).strip()

            total_ms = int((minutes * 60 + seconds) * 1000)
            lines.append((text, total_ms))

        return lines

    def add_lyrics(self, file_path: str, artist: str, title: str) -> None:
        """
        Основной метод: ищет и записывает в файл синхронизированный (SYLT)
        и обычный (USLT) тексты, если они доступны в ответе API.

        :param file_path: путь к аудиофайлу (MP3 и т.п.)
        :param artist: исполнитель
        :param title: название трека
        """
        # Получаем полные данные от API
        data = self.fetch_lyrics_data(artist, title)
        if not data:
            print(f"[LRCLIB] Данные не найдены для: {artist} - {title}")
            return

        # Извлекаем оба типа текстов
        synced_lyrics = data.get("syncedLyrics")
        plain_lyrics = data.get("plainLyrics")

        if not synced_lyrics and not plain_lyrics:
            print(f"[LRCLIB] Нет текстов (ни синхронизированного, ни обычного) для {artist} - {title}")
            return

        # Подготавливаем ID3-теги файла
        try:
            tags = ID3(file_path)
        except ID3NoHeaderError:
            tags = ID3()

        # Удаляем старые теги текстов, чтобы избежать дублирования
        tags.delall("SYLT")
        tags.delall("USLT")

        # Добавляем синхронизированный текст (SYLT), если он есть
        if synced_lyrics:
            parsed_lines = self._parse_lrc(synced_lyrics)
            if parsed_lines:
                try:
                    tags.add(
                        SYLT(
                            encoding=3,        # UTF-8
                            lang="eng",        # язык (можно изменить или определять)
                            format=2,           # миллисекунды
                            type=1,             # тип "лирика"
                            text=parsed_lines
                        )
                    )
                    print(f"[SYLT] Синхронизированный текст добавлен.")
                except Exception as e:
                    print(f"[SYLT ERROR] Не удалось добавить синхронизированный текст: {e}")
            else:
                print("[SYLT] Не удалось распарсить LRC-текст.")
        else:
            print("[SYLT] Синхронизированный текст отсутствует в ответе API.")

        # Добавляем обычный текст (USLT), если он есть
        if plain_lyrics:
            try:
                tags.add(
                    USLT(
                        encoding=3,            # UTF-8
                        lang="eng",            # язык
                        desc="Lyrics",         # описание
                        text=plain_lyrics.strip()
                    )
                )
                print(f"[USLT] Обычный текст добавлен.")
            except Exception as e:
                print(f"[USLT ERROR] Не удалось добавить обычный текст: {e}")
        else:
            print("[USLT] Обычный текст отсутствует в ответе API.")

        # 6. Сохраняем изменения, если были добавлены какие-либо теги
        if synced_lyrics or plain_lyrics:
            try:
                tags.save(file_path)
                print(f"[ID3] Теги успешно сохранены в {file_path}")
            except Exception as e:
                print(f"[ID3 ERROR] Не удалось сохранить теги: {e}")
        else:
            print("[ID3] Нечего сохранять.")

# Пример использования
if __name__ == "__main__":
    fetcher = LRCLyricsFetcher()
    # Пример из вашего запроса
    fetcher.add_lyrics("song.mp3", "Kai Angel", "SILVER CP")