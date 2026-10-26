import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List

# ponytail: simple direct subprocess calls. upgrade to async job queue (Celery/RQ) when traffic demands distributed workers.

def probe_media(file_path: str) -> Dict[str, Any]:
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    
    video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    format_info = data.get("format", {})

    duration = float(format_info.get("duration", 0.0))
    if not duration and video_stream:
        duration = float(video_stream.get("duration", 0.0))

    width = int(video_stream.get("width", 0)) if video_stream else 0
    height = int(video_stream.get("height", 0)) if video_stream else 0
    
    fps = 30.0
    if video_stream and "r_frame_rate" in video_stream:
        try:
            num, den = map(int, video_stream["r_frame_rate"].split("/"))
            fps = round(num / den, 2) if den > 0 else 30.0
        except Exception:
            fps = 30.0

    return {
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "has_audio": audio_stream is not None,
        "has_video": video_stream is not None
    }

def extract_audio(video_path: str, output_wav_path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(output_wav_path)), exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_wav_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_wav_path

def format_timestamp_srt(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

def write_srt(segments: List[Dict[str, Any]], srt_path: str, offset_start: float = 0.0) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(srt_path)), exist_ok=True)
    with open(srt_path, "w", encoding="utf-8") as f:
        for idx, seg in enumerate(segments, start=1):
            start = max(0.0, seg["start"] - offset_start)
            end = max(start + 0.1, seg["end"] - offset_start)
            f.write(f"{idx}\n")
            f.write(f"{format_timestamp_srt(start)} --> {format_timestamp_srt(end)}\n")
            f.write(f"{seg['text'].strip()}\n\n")
    return srt_path

def render_clip(
    video_path: str,
    output_path: str,
    start_time: float,
    duration: float,
    aspect_ratio: str = "9:16",
    srt_path: str | None = None
) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Filter selection based on aspect ratio
    filters = []
    if aspect_ratio == "9:16":
        # Crop center to 9:16 and scale to 720x1280
        filters.append("crop=min(iw\\,ih*9/16):min(ih\\,iw*16/9):(iw-ow)/2:(ih-oh)/2,scale=720:1280:flags=lanczos")
    elif aspect_ratio == "1:1":
        filters.append("crop=min(iw\\,ih):min(iw\\,ih):(iw-ow)/2:(ih-oh)/2,scale=720:720:flags=lanczos")
    else:  # 16:9 or original
        filters.append("scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2")

    workdir = os.path.dirname(os.path.abspath(output_path))
    if srt_path and os.path.exists(srt_path):
        rel_srt = os.path.relpath(srt_path, start=workdir).replace("\\", "/")
        # Style subtitles with clear white text and black outline
        filters.append(f"subtitles={rel_srt}:force_style='FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Alignment=2,MarginV=40'")

    filter_str = ",".join(filters)

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-t", str(duration),
        "-i", os.path.abspath(video_path),
        "-vf", filter_str,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        os.path.abspath(output_path)
    ]

    result = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {result.stderr}")

    return output_path
