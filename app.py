import subprocess
import os
import sys
import json

def get_available_formats(video_url):
    """
    Get available formats for the video using yt-dlp.
    Returns a list of formats with their details.
    """
    try:
        # Get video formats in JSON format
        process = subprocess.run(
            [
                "python", "-m", "yt_dlp",
                "--format", "bestvideo+bestaudio/best",
                "-J",  # Output JSON format
                video_url
            ],
            capture_output=True,
            text=True
        )
        
        video_info = json.loads(process.stdout)
        formats = video_info.get('formats', [])
        
        # Filter and organize formats
        available_formats = []
        seen_qualities = set()
        
        for fmt in formats:
            # Get resolution and extension
            resolution = fmt.get('resolution', 'N/A')
            ext = fmt.get('ext', 'N/A')
            filesize = fmt.get('filesize', 0)
            format_id = fmt.get('format_id', 'N/A')
            vcodec = fmt.get('vcodec', 'none')
            acodec = fmt.get('acodec', 'none')
            
            # Only add if it has both video and audio, or is video only
            if vcodec != 'none':
                # Create quality string
                quality = f"{resolution} ({ext})"
                if quality not in seen_qualities:
                    seen_qualities.add(quality)
                    available_formats.append({
                        'format_id': format_id,
                        'resolution': resolution,
                        'ext': ext,
                        'filesize': filesize,
                        'vcodec': vcodec,
                        'acodec': acodec
                    })
        
        return sorted(available_formats, key=lambda x: int(x['resolution'].split('x')[0]) if 'x' in x['resolution'] else 0, reverse=True)
    
    except Exception as e:
        print(f"Error getting video formats: {str(e)}")
        return None

def download_youtube_video(video_url, output_path="downloads", format_id=None):
    """
    Downloads a YouTube video using yt-dlp in specified quality.

    :param video_url: The URL of the YouTube video to download.
    :param output_path: Directory where the video will be saved (default: "downloads").
    :param format_id: Format ID for the desired quality.
    """
    try:
        # Create the output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)

        # Base command
        command = [
            "python", "-m", "yt_dlp",
            "--merge-output-format", "mp4",          # Merge into MP4 format
            "--output", f"{output_path}/%(title)s.%(ext)s",
            "--progress",                            # Show progress
            "--newline",                             # Force progress on new lines
        ]

        # Add format selection if specified
        if format_id:
            command.extend(["-f", f"{format_id}+bestaudio/best"])
        else:
            command.extend(["--format", "bestvideo+bestaudio/best"])

        # Add the URL
        command.append(video_url)

        # Start the download process
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )

        # Print output in real-time
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                clean_output = output.strip()
                if '[download]' in clean_output:
                    print(clean_output, flush=True)

        if process.returncode != 0:
            print("Error downloading video:")
            print(process.stderr.read())
        else:
            print("\nDownload complete!")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

def format_filesize(size_in_bytes):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} TB"

if __name__ == "__main__":
    video_url = input("Enter the YouTube video URL: ")
    
    print("\nFetching available formats...")
    formats = get_available_formats(video_url)
    
    if formats:
        print("\nAvailable qualities:")
        print("0. Best Quality (Automatic)")
        for i, fmt in enumerate(formats, 1):
            filesize = format_filesize(fmt['filesize']) if fmt['filesize'] else 'N/A'
            print(f"{i}. {fmt['resolution']} ({fmt['ext']}) - Size: {filesize}")
        
        while True:
            try:
                choice = int(input("\nSelect quality (enter number): "))
                if 0 <= choice <= len(formats):
                    break
                print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
        
        format_id = None if choice == 0 else formats[choice-1]['format_id']
        download_youtube_video(video_url, format_id=format_id)
    else:
        print("Could not fetch video formats. Downloading in best quality.")
    download_youtube_video(video_url)
