import os
import sys
import zipfile
import shutil
from urllib.request import urlretrieve
import platform

def get_ffmpeg():
    """Download and setup FFmpeg in a portable way"""
    ffmpeg_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ffmpeg')
    os.makedirs(ffmpeg_dir, exist_ok=True)

    # Determine the system and architecture
    system = platform.system().lower()
    is_64bits = sys.maxsize > 2**32

    # Define download URLs for different systems
    urls = {
        'windows': 'https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip',
        'linux': 'https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz',
        'darwin': 'https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-macos64-gpl.zip'
    }

    if not is_64bits:
        raise Exception("32-bit systems are not supported")

    if system not in urls:
        raise Exception(f"Unsupported system: {system}")

    ffmpeg_url = urls[system]
    archive_path = os.path.join(ffmpeg_dir, 'ffmpeg_archive')
    
    # Download and extract FFmpeg if not already present
    if not os.path.exists(os.path.join(ffmpeg_dir, 'ffmpeg.exe' if system == 'windows' else 'ffmpeg')):
        print("Downloading FFmpeg...")
        urlretrieve(ffmpeg_url, archive_path)
        
        print("Extracting FFmpeg...")
        if system == 'windows':
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(ffmpeg_dir)
        else:
            import tarfile
            with tarfile.open(archive_path) as tar:
                tar.extractall(ffmpeg_dir)

        # Clean up the archive
        os.remove(archive_path)

        # Move binaries to the main ffmpeg directory
        for root, dirs, files in os.walk(ffmpeg_dir):
            for file in files:
                if file.startswith('ffmpeg') or file.startswith('ffprobe'):
                    src = os.path.join(root, file)
                    dst = os.path.join(ffmpeg_dir, file)
                    shutil.move(src, dst)

        # Make binaries executable on Unix-like systems
        if system != 'windows':
            os.chmod(os.path.join(ffmpeg_dir, 'ffmpeg'), 0o755)
            os.chmod(os.path.join(ffmpeg_dir, 'ffprobe'), 0o755)

    # Clean up any remaining extracted directories
    for item in os.listdir(ffmpeg_dir):
        item_path = os.path.join(ffmpeg_dir, item)
        if os.path.isdir(item_path) and item != '__pycache__':
            shutil.rmtree(item_path)

    return ffmpeg_dir