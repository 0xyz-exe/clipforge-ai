import os
import shutil
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import init_db, get_db, Project, Transcript, TranscriptSegment, Clip, Job
from app.services.video import probe_media, extract_audio, write_srt, render_clip
from app.services.transcribe import transcribe_audio
from app.services.highlighter import generate_candidates

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
CLIPS_DIR = BASE_DIR / "storage" / "clips"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

init_db()

app = FastAPI(title="ClipForge AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background processing functions

def process_analysis_task(project_id: int):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        project.status = "analyzing"
        db.commit()

        # Step 1: Extract audio
        audio_path = str(UPLOAD_DIR / f"{project.id}_audio.wav")
        extract_audio(project.storage_path, audio_path)

        # Step 2: Transcribe with faster-whisper
        lang, segments = transcribe_audio(audio_path, model_size="tiny")

        # Step 3: Persist Transcript
        transcript = Transcript(
            project_id=project.id,
            language=lang,
            full_text=" ".join(s["text"] for s in segments)
        )
        db.add(transcript)
        db.flush()

        for seg in segments:
            db.add(TranscriptSegment(
                transcript_id=transcript.id,
                start_time=seg["start"],
                end_time=seg["end"],
                text=seg["text"]
            ))

        # Step 4: Detect Highlights
        min_dur = 5.0 if project.duration < 30.0 else 15.0
        candidates = generate_candidates(segments, project.duration, min_duration=min_dur)

        for cand in candidates:
            db.add(Clip(
                project_id=project.id,
                title=cand["title"],
                start_time=cand["start_time"],
                end_time=cand["end_time"],
                duration=cand["duration"],
                score=cand["score"],
                aspect_ratio="9:16",
                status="candidate"
            ))

        project.status = "ready"
        db.commit()
    except Exception as e:
        db.rollback()
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = "failed"
            db.commit()
    finally:
        db.close()

def process_render_task(clip_id: int, aspect_ratio: str = "9:16"):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if not clip:
            return

        clip.status = "rendering"
        clip.aspect_ratio = aspect_ratio
        db.commit()

        project = clip.project
        # Get matching transcript segments for subtitles
        srt_path = None
        if project.transcript and project.transcript.segments:
            clip_segs = [
                {"start": s.start_time, "end": s.end_time, "text": s.text}
                for s in project.transcript.segments
                if s.end_time >= clip.start_time and s.start_time <= clip.end_time
            ]
            if clip_segs:
                srt_path = str(CLIPS_DIR / f"sub_{clip.id}.srt")
                write_srt(clip_segs, srt_path, offset_start=clip.start_time)

        output_path = str(CLIPS_DIR / f"clip_{clip.id}_{aspect_ratio.replace(':', '_')}.mp4")
        render_clip(
            video_path=project.storage_path,
            output_path=output_path,
            start_time=clip.start_time,
            duration=clip.duration,
            aspect_ratio=aspect_ratio,
            srt_path=srt_path
        )

        clip.output_path = output_path
        clip.status = "ready"
        db.commit()
    except Exception as e:
        db.rollback()
        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if clip:
            clip.status = "failed"
            db.commit()
    finally:
        db.close()

# API Endpoints

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ClipForge AI",
        "storage": os.path.exists(str(UPLOAD_DIR))
    }

@app.post("/api/v1/projects")
async def create_project(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    file: UploadFile = File(...),
    auto_analyze: bool = Form(True),
    db: Session = Depends(get_db)
):
    ext = Path(file.filename or "video.mp4").suffix or ".mp4"
    saved_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = UPLOAD_DIR / saved_name

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        info = probe_media(str(dest_path))
    except Exception as e:
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(status_code=400, detail=f"Invalid video file: {str(e)}")

    project = Project(
        name=name,
        source_filename=file.filename or saved_name,
        storage_path=str(dest_path),
        duration=info["duration"],
        width=info["width"],
        height=info["height"],
        fps=info["fps"],
        status="uploaded"
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    if auto_analyze:
        background_tasks.add_task(process_analysis_task, project.id)

    return {
        "id": project.id,
        "name": project.name,
        "status": project.status,
        "duration": project.duration,
        "width": project.width,
        "height": project.height
    }

@app.get("/api/v1/projects")
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "status": p.status,
            "duration": p.duration,
            "width": p.width,
            "height": p.height,
            "clips_count": len(p.clips),
            "created_at": p.created_at.isoformat()
        }
        for p in projects
    ]

@app.get("/api/v1/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    transcript_data = None
    if p.transcript:
        transcript_data = {
            "language": p.transcript.language,
            "full_text": p.transcript.full_text,
            "segments": [
                {"id": s.id, "start": s.start_time, "end": s.end_time, "text": s.text}
                for s in p.transcript.segments
            ]
        }

    clips_data = [
        {
            "id": c.id,
            "title": c.title,
            "start_time": c.start_time,
            "end_time": c.end_time,
            "duration": c.duration,
            "score": c.score,
            "aspect_ratio": c.aspect_ratio,
            "status": c.status,
            "has_output": c.output_path is not None and os.path.exists(c.output_path)
        }
        for c in p.clips
    ]

    return {
        "id": p.id,
        "name": p.name,
        "status": p.status,
        "duration": p.duration,
        "width": p.width,
        "height": p.height,
        "fps": p.fps,
        "transcript": transcript_data,
        "clips": clips_data,
        "created_at": p.created_at.isoformat()
    }

@app.post("/api/v1/projects/{project_id}/analyze")
def trigger_analysis(project_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    background_tasks.add_task(process_analysis_task, p.id)
    return {"message": "Analysis started", "project_id": project_id}

@app.post("/api/v1/clips/{clip_id}/render")
def trigger_render(
    clip_id: int,
    background_tasks: BackgroundTasks,
    aspect_ratio: str = "9:16",
    db: Session = Depends(get_db)
):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    clip.status = "queued"
    db.commit()

    background_tasks.add_task(process_render_task, clip.id, aspect_ratio)
    return {"message": "Rendering queued", "clip_id": clip_id, "aspect_ratio": aspect_ratio}

@app.get("/api/v1/clips/{clip_id}/download")
def download_clip(clip_id: int, db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip or not clip.output_path or not os.path.exists(clip.output_path):
        raise HTTPException(status_code=404, detail="Rendered clip not ready")

    safe_name = f"clip_{clip.id}_{clip.aspect_ratio.replace(':', '_')}.mp4"
    return FileResponse(
        clip.output_path,
        media_type="video/mp4",
        filename=safe_name,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'}
    )

@app.get("/api/v1/clips/{clip_id}/stream")
def stream_clip(clip_id: int, db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip or not clip.output_path or not os.path.exists(clip.output_path):
        raise HTTPException(status_code=404, detail="Rendered clip not found")
    return FileResponse(clip.output_path, media_type="video/mp4")
