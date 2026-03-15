from TrackDownloader import TrackDownloader

def main():
    downloader = TrackDownloader(max_workers=10)

    url = input("Link on track / albom / playlist: ")

    downloader.download(url)

    print("All tracks downloaded!")

if __name__ == "__main__":
    main()