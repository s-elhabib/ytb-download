import os
import tempfile
from flask import Flask, request, jsonify, render_template
from yt_dlp import YoutubeDL
from utils.ffmpeg_downloader import get_ffmpeg  # Import the FFmpeg utility

app = Flask(__name__)

# Get the absolute path of the project directory (where app.py is located)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
# Create downloads directory path
DOWNLOAD_DIR = os.path.join(PROJECT_DIR, 'downloads')

# Create the downloads directory if it doesn't exist
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Setup portable FFmpeg
FFMPEG_PATH = get_ffmpeg()

# Add this class at the top of your file, after the imports
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

# Create a global progress hook instance
progress_tracker = ProgressHook()

@app.route('/')
def index():
    return render_template('index.html')

def format_size(bytes):
    """Convert bytes to human readable string"""
    if not bytes:
        return "N/A"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} TB"

@app.route('/api/formats', methods=['POST'])
def get_formats():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400

        url = data['url']
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': FFMPEG_PATH,  # Add FFmpeg location
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            response_data = {
                'title': info.get('title', 'Unknown Title'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'formats': []
            }
            
            # Add best quality option
            response_data['formats'].append({
                'format_id': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'resolution': 'Best Quality',
                'ext': 'mp4',
                'filesize': 'Automatic',
                'height': 9999  # For sorting
            })
            
            # Get all video formats
            all_formats = []
            for f in info.get('formats', []):
                # Include formats with video codec
                if f.get('vcodec', 'none') != 'none':
                    height = f.get('height', 0)
                    if height:  # Only include formats with height information
                        all_formats.append({
                            'format_id': f['format_id'],
                            'resolution': f"{height}p",
                            'ext': f.get('ext', 'mp4'),
                            'filesize': format_size(f.get('filesize', 0)),
                            'height': height
                        })
            
            # Sort by height (resolution) in descending order
            all_formats = sorted(all_formats, key=lambda x: x['height'], reverse=True)
            
            # Target resolutions we want to show
            target_resolutions = [1080, 720, 360, 144]
            
            # For each target resolution, find the closest available format
            for target in target_resolutions:
                closest_format = None
                min_diff = float('inf')
                
                for fmt in all_formats:
                    diff = abs(fmt['height'] - target)
                    if diff < min_diff:
                        min_diff = diff
                        closest_format = fmt.copy()  # Make a copy to avoid modifying the original
                
                # If we found a format, add it with the target resolution label
                if closest_format:
                    # Update the resolution label to match our target
                    closest_format['resolution'] = f"{target}p"
                    # Add filesize info if available
                    if closest_format['filesize'] != 'N/A':
                        closest_format['resolution'] += f" (mp4) - Size: {closest_format['filesize']}"
                    else:
                        closest_format['resolution'] += f" (mp4)"
                    # Update format_id to ensure we get both video and audio
                    closest_format['format_id'] = f"{closest_format['format_id']}+bestaudio[ext=m4a]/bestaudio"
                    response_data['formats'].append(closest_format)
                else:
                    # If no format is available, create a placeholder that uses the best format
                    response_data['formats'].append({
                        'format_id': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                        'resolution': f"{target}p (mp4) - Size: Automatic",
                        'ext': 'mp4',
                        'filesize': 'Automatic',
                        'height': target
                    })
            
            # Add MP3 audio option at the end
            # Find best audio format for size estimation
            best_audio = None
            for f in info.get('formats', []):
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    if best_audio is None or (f.get('filesize', 0) and f.get('filesize', 0) > best_audio.get('filesize', 0)):
                        best_audio = f
            
            audio_size = format_size(best_audio.get('filesize', 0)) if best_audio else 'Automatic'
            response_data['formats'].append({
                'format_id': 'bestaudio/best',
                'resolution': f"Audio Only (mp3) - Size: {audio_size}",
                'ext': 'mp3',
                'filesize': audio_size,
                'height': 0  # Lowest priority for sorting
            })
            
            return jsonify(response_data)

    except Exception as e:
        print("Error:", str(e))
        return jsonify({'error': str(e)}), 400

@app.route('/api/progress')
def get_progress():
    # This endpoint will be polled by the frontend to get download progress
    return jsonify(progress_tracker.progress)

@app.route('/api/download', methods=['POST'])
def download_video():
    try:
        data = request.get_json()
        if not data or 'url' not in data or 'format_id' not in data:
            return jsonify({'error': 'URL and format_id are required'}), 400

        url = data['url']
        format_id = data['format_id']
        
        # Use system's temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts = {
                'format': format_id,
                'quiet': True,
                'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
                'merge_output_format': 'mp4',  # Default for video
                'ffmpeg_location': FFMPEG_PATH,
                'progress_hooks': [progress_tracker],
            }
            
            # Check if this is an audio-only download
            if format_id == 'bestaudio/best':
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            else:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }]
                
            ydl_opts['paths'] = {
                'home': DOWNLOAD_DIR,
                'temp': temp_dir,
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
