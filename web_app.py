from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from yt_dlp import YoutubeDL
from utils.ffmpeg_downloader import get_ffmpeg

app = Flask(__name__)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Setup portable FFmpeg
FFMPEG_PATH = get_ffmpeg()

def get_ydl_opts(format_id=None):
    """Get yt-dlp options with FFmpeg configuration"""
    return {
        'format': format_id if format_id else 'bestvideo+bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'ffmpeg_location': FFMPEG_PATH,
    }

def format_size(bytes):
    """Convert bytes to human readable format"""
    if not bytes:
        return 'N/A'
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} GB"

def get_format_info(f):
    """Extract and format information about a video/audio format"""
    vcodec = f.get('vcodec', 'none')
    acodec = f.get('acodec', 'none')
    
    # Only include formats with both video and audio
    if vcodec != 'none' and acodec != 'none':
        return {
            'format_id': f['format_id'],
            'resolution': f.get('resolution', 'N/A'),
            'ext': f['ext'],
            'filesize': format_size(f.get('filesize', 0)),
            'vcodec': vcodec,
            'acodec': acodec,
            'tbr': f.get('tbr', 0)
        }
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/formats', methods=['POST'])
def get_formats():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        with YoutubeDL(get_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Add best quality option first
            formats = [{
                'format_id': 'best',
                'resolution': 'Best Quality',
                'ext': 'Automatic',
                'filesize': '',
                'vcodec': 'best',
                'acodec': 'best',
                'tbr': 0  # Changed from float('inf') to 0
            }]
            
            # Process formats with both video and audio
            for f in info['formats']:
                format_info = get_format_info(f)
                if format_info:
                    formats.append(format_info)

            # Sort formats by resolution (excluding the first "Best Quality" option)
            def get_resolution_value(fmt):
                if fmt['resolution'] == 'Best Quality':
                    return float('inf')
                res = fmt['resolution'].split('x')[0]
                return int(res) if res.isdigit() else 0

            first_format = formats[0]
            remaining_formats = sorted(formats[1:], 
                                    key=get_resolution_value,
                                    reverse=True)
            formats = [first_format] + remaining_formats

            return jsonify({
                'title': info['title'],
                'thumbnail': info['thumbnail'],
                'duration': info['duration'],
                'formats': formats
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/download', methods=['POST'])
def download():
    url = request.json.get('url')
    format_id = request.json.get('format_id')

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        with YoutubeDL(get_ydl_opts(format_id)) as ydl:
            ydl.download([url])
        
        return jsonify({'success': True, 'message': 'Download completed successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
