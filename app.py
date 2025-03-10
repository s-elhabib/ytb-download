import os
import tempfile
import logging
from flask import Flask, request, jsonify, render_template
from yt_dlp import YoutubeDL
from utils.ffmpeg_downloader import get_ffmpeg  # Import the FFmpeg utility
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        self.progress = {
            'status': 'idle',
            'downloaded_bytes': 0,
            'total_bytes': 0,
            'speed': 0,
            'eta': 0,
            'percentage': 0,
            'filename': ''
        }

    def __call__(self, d):
        logger.info(f"Progress update: {d['status']}")
        
        if d['status'] == 'downloading':
            self.progress['status'] = 'downloading'
            self.progress['downloaded_bytes'] = d.get('downloaded_bytes', 0)
            self.progress['total_bytes'] = d.get('total_bytes', 0)
            self.progress['speed'] = d.get('speed', 0)
            self.progress['eta'] = d.get('eta', 0)
            self.progress['filename'] = d.get('filename', '')
            
            if d.get('total_bytes'):
                self.progress['percentage'] = (d['downloaded_bytes'] / d['total_bytes']) * 100
                logger.info(f"Download progress: {self.progress['percentage']:.2f}%")
            elif d.get('total_bytes_estimate'):
                self.progress['percentage'] = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                logger.info(f"Download progress (estimate): {self.progress['percentage']:.2f}%")
            else:
                logger.info(f"Download progress: unknown (no total bytes)")
        
        elif d['status'] == 'finished':
            logger.info("Download finished!")
            self.progress['status'] = 'finished'
            self.progress['percentage'] = 100

# Create a global progress hook instance that persists between requests
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
    # Log the current progress data
    logger.info(f"Progress data: {progress_tracker.progress}")
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
        resolution = data.get('resolution', '')

        # Reset progress tracker for new download
        progress_tracker.progress = {
            'status': 'starting',
            'downloaded_bytes': 0,
            'total_bytes': 0,
            'speed': 0,
            'eta': 0,
            'percentage': 0,
            'filename': ''
        }

        # Extract resolution value from the string
        if resolution:
            resolution_value = resolution.split()[0]
        else:
            if format_id == 'bestaudio/best':
                resolution_value = "MP3"
            elif format_id.startswith('bestvideo'):
                resolution_value = "BEST"
            else:
                resolution_value = "MP4"

        def format_size(bytes):
            """Convert bytes to human readable string"""
            if not bytes:
                return "0 B"
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes < 1024:
                    return f"{bytes:.1f} {unit}"
                bytes /= 1024
            return f"{bytes:.1f} TB"

        def format_speed(speed):
            """Convert speed to human readable string"""
            return f"{format_size(speed)}/s" if speed else "0 B/s"

        def progress_hook(d):
            progress_tracker(d)
            if d['status'] == 'downloading':
                try:
                    # Get downloaded bytes
                    downloaded_bytes = d.get('downloaded_bytes', 0)
                    
                    # Get total bytes or estimate
                    total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    
                    # Calculate percentage only if we have valid total bytes
                    if total_bytes > 0:
                        percentage = (downloaded_bytes / total_bytes) * 100
                    else:
                        percentage = 0
                    
                    # Get speed and eta
                    speed = d.get('speed', 0)
                    eta = d.get('eta', 0)
                    
                    # Format the values
                    speed_str = format_speed(speed)
                    downloaded_str = format_size(downloaded_bytes)
                    total_str = format_size(total_bytes) if total_bytes else 'Unknown'
                    eta_str = f"{int(eta//60)}:{int(eta%60):02d}" if eta else "??:??"

                    # Clear line and print progress
                    print(f"\rDownloading: {percentage:5.1f}% | {downloaded_str}/{total_str} | Speed: {speed_str} | ETA: {eta_str}", 
                          end='', flush=True)
                except Exception as e:
                    # If there's any error in progress calculation, just show basic status
                    print(f"\rDownloading... {format_size(d.get('downloaded_bytes', 0))}", end='', flush=True)
            
            elif d['status'] == 'finished':
                print("\nDownload completed!")

        # Add timestamp to filename to make it unique
        timestamp = int(time.time())
        filename_template = os.path.join(DOWNLOAD_DIR, f'%(title)s (%(resolution)s)_{timestamp}.%(ext)s')

        # Use system's temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts = {
                'format': format_id,
                'outtmpl': filename_template,
                'merge_output_format': 'mp4',
                'ffmpeg_location': FFMPEG_PATH,
                'progress_hooks': [progress_hook],
                'outtmpl_params': {
                    'resolution': resolution_value,
                },
                'quiet': True,
                'no_warnings': True,
                'force_download': True,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'keepvideo': False,
                'clean_infojson': True,
                'postprocessor_args': ['-y'],
                'paths': {
                    'home': DOWNLOAD_DIR,
                    'temp': temp_dir,
                }
            }

            # Check if this is an audio-only download
            if format_id == 'bestaudio/best':
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
                ydl_opts['extract_audio'] = True
                ydl_opts['format'] = 'bestaudio'
            else:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }]
                ydl_opts['format'] = format_id

            try:
                with YoutubeDL(ydl_opts) as ydl:
                    logger.info("Starting YoutubeDL download...")
                    ydl.download([url])
                    logger.info("Download completed successfully")

                # Clean up any remaining .part files
                for file in os.listdir(DOWNLOAD_DIR):
                    if file.endswith('.part') or file.endswith('.ytdl'):
                        try:
                            os.remove(os.path.join(DOWNLOAD_DIR, file))
                        except:
                            pass

            except Exception as e:
                logger.error(f"Error during download: {str(e)}")
                raise

        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        progress_tracker.progress['status'] = 'error'
        progress_tracker.progress['error'] = str(e)
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
