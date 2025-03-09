# YouTube Video Downloader

A Python script that allows you to download YouTube videos in your preferred quality using yt-dlp. This tool provides a user-friendly interface to select video quality and shows download progress in real-time.

## Features

- Download YouTube videos in various qualities
- Show available video formats and their sizes
- Real-time download progress tracking
- Automatic video and audio merging
- Support for high-quality video downloads

## Prerequisites

Before running the script, you need to have the following installed:

1. Python 3.8 or higher
2. FFmpeg (required for merging video and audio)
3. yt-dlp Python package

### Installing FFmpeg

#### Windows
Option 1: Using winget (Windows 11)
```bash
winget install FFmpeg
```

Option 2: Manual installation
1. Download FFmpeg from [FFmpeg Builds](https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip)
2. Extract the zip file
3. Add the `bin` folder to your system's PATH environment variable

#### macOS
Using Homebrew:
```bash
brew install ffmpeg
```

#### Linux
```bash
sudo apt update
sudo apt install ffmpeg
```

### Installing Required Python Packages

```bash
pip install yt-dlp
```

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/youtube-video-downloader.git
cd youtube-video-downloader
```

2. Install the required Python packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the script:
```bash
python app.py
```

2. Enter the YouTube video URL when prompted

3. Select your preferred video quality from the available options:
   - Option 0: Best quality (automatic)
   - Options 1-N: Specific quality formats

4. Wait for the download to complete. Progress will be shown in real-time.

Example output:
```
Enter the YouTube video URL: https://www.youtube.com/watch?v=...

Fetching available formats...

Available qualities:
0. Best Quality (Automatic)
1. 1920x1080 (mp4) - Size: 158.72 MB
2. 1280x720 (mp4) - Size: 82.45 MB
3. 854x480 (mp4) - Size: 45.12 MB
4. 640x360 (mp4) - Size: 25.34 MB

Select quality (enter number): 1

[download] Downloading video ...
[download]   5.7% of 158.72MiB at  1.2MiB/s ETA 02:15
...
[download] 100% of 158.72MiB
Download complete!
```

## Output

Downloaded videos are saved in the `downloads` directory by default. The filename will be the video's title with the appropriate extension (usually .mp4).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for the YouTube download functionality
- [FFmpeg](https://ffmpeg.org/) for video processing capabilities

## Disclaimer

This tool is for personal use only. Please respect YouTube's terms of service and content creators' rights when downloading videos.

```bash
git remote set-url origin git@github.com:s-elhabib/ytb-download.git
```

```bash
git push -u origin main
```

