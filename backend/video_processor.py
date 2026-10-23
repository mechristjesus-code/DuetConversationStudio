import subprocess
import json
import hashlib
from pathlib import Path

def get_video_metadata(file_path: str):
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", file_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        duration = float(data.get("format", {}).get("duration", 0.0))
        width, height = 0, 0
        has_audio = False
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                width = int(stream.get("width", 0))
                height = int(stream.get("height", 0))
            elif stream.get("codec_type") == "audio":
                has_audio = True
        return {"duration": duration, "width": width, "height": height, "has_audio": has_audio}
    except Exception as e:
        print(f"Error getting video metadata for {file_path}: {e}")
        return {"duration": 0.0, "width": 0, "height": 0, "has_audio": False}

def compute_checksum(file_path: str):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def trim_video(input_path: str, output_path: str, start_sec: float, duration_sec: float):
    cmd = [
        "ffmpeg", "-y", "-ss", str(start_sec), "-i", input_path,
        "-t", str(duration_sec), "-c:v", "libx264", "-c:a", "aac", output_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg trim failed: {res.stderr}")

def render_duet(video1_path: str, video2_path: str, output_path: str, layout: str = "side-by-side", trim1=None, trim2=None):
    # trim1, trim2: dict with {"start": float, "duration": float} optional
    
    meta1 = get_video_metadata(video1_path)
    meta2 = get_video_metadata(video2_path)
    
    cmd = ["ffmpeg", "-y"]
    
    if trim1 and "start" in trim1:
        cmd.extend(["-ss", str(trim1["start"])])
    if trim1 and "duration" in trim1:
        cmd.extend(["-t", str(trim1["duration"])])
    cmd.extend(["-i", video1_path])
    
    if trim2 and "start" in trim2:
        cmd.extend(["-ss", str(trim2["start"])])
    if trim2 and "duration" in trim2:
        cmd.extend(["-t", str(trim2["duration"])])
    cmd.extend(["-i", video2_path])
    
    has_a1 = meta1["has_audio"]
    has_a2 = meta2["has_audio"]
    
    if layout == "side-by-side":
        v_filter = "[0:v]scale=640:1136,setsar=1[v0];[1:v]scale=640:1136,setsar=1[v1];[v0][v1]hstack=inputs=2[outv]"
    else:
        v_filter = "[0:v]scale=720:640,setsar=1[v0];[1:v]scale=720:640,setsar=1[v1];[v0][v1]vstack=inputs=2[outv]"
        
    if has_a1 and has_a2:
        filter_complex = f"{v_filter};[0:a][1:a]amix=inputs=2[outa]"
        map_args = ["-map", "[outv]", "-map", "[outa]"]
    elif has_a1:
        filter_complex = f"{v_filter};[0:a]anull[outa]"
        map_args = ["-map", "[outv]", "-map", "[outa]"]
    elif has_a2:
        filter_complex = f"{v_filter};[1:a]anull[outa]"
        map_args = ["-map", "[outv]", "-map", "[outa]"]
    else:
        filter_complex = v_filter
        map_args = ["-map", "[outv]"]
        
    cmd.extend(["-filter_complex", filter_complex])
    cmd.extend(map_args)
    cmd.extend(["-c:v", "libx264", "-c:a", "aac", output_path])
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg render failed: {res.stderr}")
