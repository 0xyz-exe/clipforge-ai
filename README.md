# ClipForge AI — Advanced AI Video Auto Clipper

Platform otomatisasi pemrosesan video panjang menjadi klip vertikal pendek (TikTok/Shorts/Reels) dengan transkripsi AI dan burned-in subtitles.

---

## Arsitektur

- **Frontend**: Next.js 16 (App Router), React, TypeScript, Tailwind CSS, Lucide icons
- **Backend**: FastAPI (Python 3.12), SQLAlchemy 2.0, Pydantic
- **Video Engine**: FFmpeg 9.0 + FFprobe (ekstraksi metadata, cropping dinamis 9:16 / 1:1 / 16:9, subtitle burn filter)
- **Speech-to-Text**: `faster-whisper` (model `tiny` on CPU / zero GPU mandate)
- **Highlight Heuristic**: Sentence & hook boundary analysis, speech density scoring, deduplikasi klip kandidat

---

## Persiapan & Menjalankan Aplikasi

### 1. Backend (FastAPI)

```bash
cd backend
# Menggunakan venv Python 3.12
../.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Swagger API Docs tersedia di: `http://127.0.0.1:8000/docs`

### 2. Frontend (Next.js)

```bash
cd frontend
npm run dev
# Atau production build:
npm run build && npm start
```

Web UI tersedia di: `http://localhost:3000`

---

## Verifikasi Pipeline (Automated Test)

Jalankan test end-to-end tanpa memerlukan video eksternal (FFmpeg menghasilkan video sintesis 10 detik, membedah metadata, ekstraksi audio, kalkulasi kandidat klip, dan merender video vertikal 9:16 bersubtitle):

```bash
cd backend
../.venv/Scripts/python -m tests.test_pipeline
```
