from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from yt_dlp import YoutubeDL
from utils.ffmpeg_downloader import get_ffmpeg

app = Flask(__name__)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Setup portable FFmpeg
FFMPEG_PATH = get_ffmpeg()

class ProgressHook:
    def __init__(self):
        self.progress = {}

    def __call__(self, d):
        if d['status'] == 'downloading':
            self.progress['status'] = 'downloading'
            self.progress['downloaded_bytes'] = d.get('downloaded_bytes', 0)
            self.progress['total_bytes'] = d.get('total_bytes', 0)
            self.progress['speed'] = d.get('speed', 0)
            self.progress['eta'] = d.get('eta', 0)
            if d.get('total_bytes'):
                self.progress['percentage'] = (d['downloaded_bytes'] / d['total_bytes']) * 100
            elif d.get('total_bytes_estimate'):
                self.progress['percentage'] = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
        elif d['status'] == 'finished':
            self.progress['status'] = 'finished'

def get_ydl_opts(format_id=None, progress_hook=None):
    """Get yt-dlp options with FFmpeg configuration"""
    opts = {
        'format': format_id if format_id else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'ffmpeg_location': FFMPEG_PATH,
        'merge_output_format': 'mp4',  # Force MP4 as output
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }
    if progress_hook:
        opts['progress_hooks'] = [progress_hook]
    return opts

def format_filesize(bytes):
    """Convert bytes to human readable string"""
    if not bytes:
        return "N/A"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} TB"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/formats', methods=['POST'])
def get_formats():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            formats = []
            # Get best audio format (prefer m4a for compatibility with mp4)
            best_audio = next(
                (f for f in info['formats'] 
                 if f.get('vcodec') == 'none' 
                 and f.get('acodec') != 'none'
                 and f.get('ext') == 'm4a'),
                None
            )
            
            # Add "Best Quality" option first
            formats.append({
                'format_id': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'resolution': 'Best Quality',
                'ext': 'mp4',
                'filesize': 'Automatic',
                'height': 99999,  # for sorting
                'fps': 99999,     # for sorting
            })
            
            # Process available formats
            for format in info['formats']:
                # Skip audio-only formats
                if format.get('vcodec') == 'none':
                    continue
                
                # Get resolution
                height = format.get('height', 0)
                width = format.get('width', 0)
                
                if not height or not width:
                    continue

                # Skip non-MP4 formats
                if format.get('ext') != 'mp4':
                    continue
                
                # Calculate total size including audio
                video_size = format.get('filesize', 0) or format.get('filesize_approx', 0) or 0
                audio_size = (best_audio.get('filesize', 0) or best_audio.get('filesize_approx', 0) or 0) if best_audio else 0
                total_size = video_size + audio_size

                formats.append({
                    'format_id': f"{format['format_id']}+bestaudio[ext=m4a]/bestaudio",
                    'resolution': f"{width}x{height}",
                    'ext': 'mp4',
                    'filesize': format_filesize(total_size),
                    'height': height,
                    'fps': format.get('fps', 0) or 0,
                })

            # Sort formats by resolution (height) and fps
            formats = sorted(formats, key=lambda x: (x['height'], x['fps']), reverse=True)

            # Remove duplicates based on resolution
            seen_resolutions = set()
            unique_formats = []
            for f in formats:
                resolution = f['resolution']
                if resolution not in seen_resolutions:
                    seen_resolutions.add(resolution)
                    unique_formats.append(f)

            return jsonify({
                'title': info['title'],
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration', 0),
                'formats': unique_formats
            })

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/download', methods=['POST'])
def download():
    url = request.json.get('url')
    format_id = request.json.get('format_id')

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        progress_hook = ProgressHook()
        with YoutubeDL(get_ydl_opts(format_id, progress_hook)) as ydl:
            ydl.download([url])
        return jsonify({'success': True, 'message': 'Download completed successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/progress')
def get_progress():
    # This endpoint will be polled by the frontend to get download progress
    progress_hook = ProgressHook()
    return jsonify(progress_hook.progress)

if __name__ == '__main__':
    app.run(debug=True)
