import os
from dotenv import load_dotenv
from TrackDownloader import TrackDownloader

def main():
    # Загружаем переменные из .env файла
    load_dotenv()

    # Читаем настройки (если не указаны, оставляем None – будут использованы значения по умолчанию в классе)
    download_folder = os.getenv("DOWNLOAD_FOLDER")  # строка или None
    max_workers_str = os.getenv("MAX_WORKERS")

    # Преобразуем max_workers в int, если задано
    max_workers = None
    if max_workers_str is not None:
        try:
            max_workers = int(max_workers_str)
            if max_workers <= 0:
                print("MAX_WORKERS должно быть положительным числом. Используется значение по умолчанию.")
                max_workers = None
        except ValueError:
            print("MAX_WORKERS должно быть целым числом. Используется значение по умолчанию.")

    # Создаём загрузчик с параметрами из .env (или дефолтными)
    downloader = TrackDownloader(
        download_folder=download_folder if download_folder else "downloads",
        max_workers=max_workers if max_workers is not None else 4
    )

    url = input("Link to the track / album / playlist: ")
    downloader.download(url)
    print("All tracks are downloaded!")

if __name__ == "__main__":
    main()