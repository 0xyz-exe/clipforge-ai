import os
import subprocess
from pathlib import Path
from app.services.video import probe_media, extract_audio, write_srt, render_clip
from app.services.highlighter import generate_candidates

# ponytail: synthetic test clip generator with ffmpeg. upgrade to full fixture suite when real test footage stored in git-lfs.

def test_full_pipeline():
    test_dir = Path(__file__).resolve().parent / "fixtures"
    test_dir.mkdir(parents=True, exist_ok=True)
    video_path = test_dir / "sample_test.mp4"
    audio_path = test_dir / "sample_audio.wav"
    output_clip_path = test_dir / "output_clip_9_16.mp4"
    srt_path = test_dir / "test_subtitles.srt"

    # Step 1: Generate a synthetic 10-second 1280x720 video with a test audio tone
    print("[1] Generating synthetic video...")
    gen_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=10:size=1280x720:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=10",
        "-c:v", "libx264", "-c:a", "aac",
        str(video_path)
    ]
    subprocess.run(gen_cmd, capture_output=True, check=True)
    assert video_path.exists(), "Synthetic video generation failed"

    # Step 2: Probe media
    print("[2] Probing media with ffprobe...")
    info = probe_media(str(video_path))
    assert info["width"] == 1280
    assert info["height"] == 720
    assert info["duration"] >= 9.9
    assert info["has_audio"] is True
    print(f"    Probed: {info['width']}x{info['height']}, {info['duration']}s, fps={info['fps']}")

    # Step 3: Extract audio
    print("[3] Extracting audio...")
    extract_audio(str(video_path), str(audio_path))
    assert audio_path.exists()
    print("    Audio extracted successfully.")

    # Step 4: Highlight detection
    print("[4] Generating highlight candidates...")
    mock_segments = [
        {"start": 1.0, "end": 4.5, "text": "Why this AI tool is completely game changing!"},
        {"start": 4.5, "end": 9.0, "text": "You can transform long videos into viral shorts automatically."}
    ]
    candidates = generate_candidates(mock_segments, total_duration=info["duration"], min_duration=5.0, max_duration=10.0)
    assert len(candidates) > 0
    candidate = candidates[0]
    print(f"    Selected candidate: {candidate['title']} ({candidate['start_time']}s - {candidate['end_time']}s, score={candidate['score']})")

    # Step 5: Subtitle generation
    print("[5] Generating subtitles...")
    write_srt(mock_segments, str(srt_path), offset_start=candidate["start_time"])
    assert srt_path.exists()

    # Step 6: Render clip (9:16 vertical crop with burned-in subtitles)
    print("[6] Rendering 9:16 vertical clip with burned subtitles...")
    render_clip(
        video_path=str(video_path),
        output_path=str(output_clip_path),
        start_time=candidate["start_time"],
        duration=candidate["duration"],
        aspect_ratio="9:16",
        srt_path=str(srt_path)
    )
    assert output_clip_path.exists(), "Rendered clip does not exist"

    # Step 7: Probe rendered output
    print("[7] Verifying rendered clip dimensions and format...")
    clip_info = probe_media(str(output_clip_path))
    print(f"    Rendered output: {clip_info['width']}x{clip_info['height']}, duration: {clip_info['duration']}s")
    assert clip_info["width"] == 720
    assert clip_info["height"] == 1280
    assert clip_info["has_video"] is True
    assert clip_info["has_audio"] is True

    print("\n[SUCCESS] Pipeline verified: End-to-end video processing works completely.")

if __name__ == "__main__":
    test_full_pipeline()
