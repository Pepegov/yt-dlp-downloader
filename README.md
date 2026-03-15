# Track Downloader

A script for downloading audio tracks, albums, and playlists from Spotify and YouTube (and other platforms supported by `yt-dlp`).  
It automatically sets ID3 tags (artist, album, track number, albumartist), embeds the thumbnail, and saves files into a structured folder.

## Features

- Download a single track, an entire album, or a playlist via a link.
- Multi-threaded download (number of threads is configurable).
- Convert to MP3 with 192 kbps bitrate.
- Embed thumbnail into the file.
- Set tags: `artist`, `album`, `tracknumber`, `albumartist` (for correct grouping in players).
- File naming template:  
  - For album tracks: `{number:02d} - {artist} - {title}.mp3`  
  - For single tracks: `{artist} - {title}.mp3`

## Requirements

- Python 3.6 or higher
- **ffmpeg** (must be installed on your system and available in PATH)  
  [Download ffmpeg](https://ffmpeg.org/download.html)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/track-downloader.git
   cd track-downloader
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate      # Linux/macOS
   venv\Scripts\activate         # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt   
   ```
   or install the package in editable mode (recommended):
   ```bash
   pip install -e .
   ```

## Usage

### Run the script directly
```bash
python src/main.py
```
The program will ask for a link to a track, album, or playlist. After entering it, downloading will start.

### Run via installed command
If you installed the package with `pip install -e .`, you can use the command:
```bash
track-downloader
```

### Example links

- Single track:  
  `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
- Playlist / album:  
  `https://www.youtube.com/playlist?list=PL...`

### Saved files structure

All downloads are saved into the `downloads/` folder (created automatically).  
Inside it, a folder is created with the artist's name (taken from the video's `uploader`).  
If an album/playlist is downloaded, a subfolder with the album/playlist name is created inside the artist's folder.

Example:
```
downloads/
└── Artist Name/
    ├── Album Name/
    │   ├── 01 - Artist Name - Song One.mp3
    │   ├── 02 - Artist Name - Song Two.mp3
    │   └── ...
    └── Artist Name - Single Track.mp3
```

## Configuration

In the `TrackDownloader.py` file you can change the parameters:

- `download_folder` – folder for saving (default `"downloads"`)
- `max_workers` – number of parallel threads (default 4)

## Notes

- For playlists, `yt-dlp` is used with the `extract_flat` option, so track information is retrieved quickly without downloading.
- The `albumartist` ID3 tag is set equal to the artist, which improves album display in players (e.g., MusicBee, foobar2000).
- If a file with the same name already exists, a counter is added to the name (e.g., `Artist - Song_1.mp3`).

## Dependencies

- `yt-dlp` – downloading from YouTube and other sites
- `mutagen` – handling ID3 tags

You can install them manually:
```bash
pip install yt-dlp mutagen
```