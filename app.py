from flask import Flask, request, jsonify
from yt_dlp import YoutubeDL

app = Flask(__name__)

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
                'format_id': 'best',
                'resolution': 'Best Quality',
                'ext': 'Automatic',
                'filesize': '',
                'vcodec': 'best',
                'acodec': 'best',
                'tbr': 0  # Use 0 instead of Infinity
            })
            
            # Add other formats
            for f in info.get('formats', []):
                if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') != 'none':
                    format_data = {
                        'format_id': f['format_id'],
                        'resolution': f.get('resolution', 'N/A'),
                        'ext': f.get('ext', 'N/A'),
                        'filesize': format_size(f.get('filesize', 0)),
                        'vcodec': f.get('vcodec', 'N/A'),
                        'acodec': f.get('acodec', 'N/A'),
                        'tbr': float(f.get('tbr', 0)) if f.get('tbr') is not None else 0
                    }
                    response_data['formats'].append(format_data)
            
            return jsonify(response_data)

    except Exception as e:
        print("Error:", str(e))
        return jsonify({'error': str(e)}), 400

@app.route('/api/download', methods=['POST'])
def download_video():
    try:
        data = request.get_json()
        if not data or 'url' not in data or 'format_id' not in data:
            return jsonify({'error': 'URL and format_id are required'}), 400

        url = data['url']
        format_id = data['format_id']
        
        ydl_opts = {
            'format': format_id,
            'quiet': True,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
