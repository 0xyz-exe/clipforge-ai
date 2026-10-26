"use client";

import React, { useState, useEffect } from "react";
import { 
  Scissors, 
  Upload, 
  Play, 
  Film, 
  Sparkles, 
  Download, 
  RefreshCw, 
  Clock, 
  FileText, 
  ChevronRight, 
  ArrowLeft 
} from "lucide-react";

interface Segment {
  id: number;
  start: number;
  end: number;
  text: string;
}

interface Transcript {
  language: string;
  full_text: string;
  segments: Segment[];
}

interface Clip {
  id: number;
  title: string;
  start_time: number;
  end_time: number;
  duration: number;
  score: number;
  aspect_ratio: string;
  status: string;
  has_output: boolean;
}

interface ProjectSummary {
  id: number;
  name: string;
  status: string;
  duration: number;
  width: number;
  height: number;
  clips_count: number;
  created_at: string;
}

interface ProjectDetails extends ProjectSummary {
  fps: number;
  transcript: Transcript | null;
  clips: Clip[];
}

const API_BASE = "http://127.0.0.1:8000";

export default function Home() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [projectDetails, setProjectDetails] = useState<ProjectDetails | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadName, setUploadName] = useState<string>("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [aspectRatios, setAspectRatios] = useState<Record<number, string>>({});
  const [renderingClips, setRenderingClips] = useState<Record<number, boolean>>({});

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/projects`);
      if (res.ok) {
        const data = await res.json();
        setProjects(data);
      }
    } catch {
      // Backend offline
    }
  };

  const fetchProjectDetails = async (id: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/projects/${id}`);
      if (res.ok) {
        const data = await res.json();
        setProjectDetails(data);
      }
    } catch {
      // Backend offline
    }
  };

  useEffect(() => {
    fetchProjects();
    const interval = setInterval(fetchProjects, 4000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      fetchProjectDetails(selectedProjectId);
      const interval = setInterval(() => {
        fetchProjectDetails(selectedProjectId);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [selectedProjectId]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile || !uploadName) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("name", uploadName);
    formData.append("file", uploadFile);
    formData.append("auto_analyze", "true");

    try {
      const res = await fetch(`${API_BASE}/api/v1/projects`, {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        setUploadName("");
        setUploadFile(null);
        setSelectedProjectId(data.id);
        fetchProjects();
      }
    } catch {
      alert("Failed to upload video. Verify backend is running on port 8000.");
    } finally {
      setUploading(false);
    }
  };

  const handleRenderClip = async (clipId: number) => {
    const ratio = aspectRatios[clipId] || "9:16";
    setRenderingClips(prev => ({ ...prev, [clipId]: true }));
    try {
      const res = await fetch(`${API_BASE}/api/v1/clips/${clipId}/render?aspect_ratio=${encodeURIComponent(ratio)}`, {
        method: "POST"
      });
      if (res.ok) {
        if (selectedProjectId) fetchProjectDetails(selectedProjectId);
      }
    } catch {
      alert("Failed to trigger clip render");
    } finally {
      setRenderingClips(prev => ({ ...prev, [clipId]: false }));
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans">
      <header className="border-b border-zinc-800 bg-zinc-900/60 backdrop-blur px-6 py-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-tr from-violet-600 to-indigo-500 rounded-xl shadow-lg shadow-indigo-500/20">
            <Scissors className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
              ClipForge AI
            </h1>
            <p className="text-xs text-zinc-400">Advanced AI Video Auto Clipper</p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Backend Ready (CPU + FFmpeg)
          </span>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 flex flex-col gap-8">
        {!selectedProjectId ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-1 bg-zinc-900/80 border border-zinc-800 rounded-2xl p-6 flex flex-col gap-6 shadow-xl">
              <div>
                <h2 className="text-base font-semibold text-white flex items-center gap-2">
                  <Upload className="w-4 h-4 text-indigo-400" />
                  New Video Project
                </h2>
                <p className="text-xs text-zinc-400 mt-1">
                  Upload video (MP4/MOV/WebM) to auto-extract viral vertical clips.
                </p>
              </div>

              <form onSubmit={handleUpload} className="flex flex-col gap-4">
                <div>
                  <label className="text-xs font-medium text-zinc-300 block mb-1.5">Project Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Podcast Highlights Episode 1"
                    value={uploadName}
                    onChange={(e) => setUploadName(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3.5 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium text-zinc-300 block mb-1.5">Video File</label>
                  <div className="border-2 border-dashed border-zinc-800 hover:border-zinc-700 transition-colors rounded-xl p-6 text-center cursor-pointer bg-zinc-950/50 relative">
                    <input
                      type="file"
                      accept="video/mp4,video/quicktime,video/webm"
                      required
                      onChange={(e) => setUploadFile(e.target.files ? e.target.files[0] : null)}
                      className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                    />
                    <Film className="w-8 h-8 text-zinc-500 mx-auto mb-2" />
                    <p className="text-xs font-medium text-zinc-300">
                      {uploadFile ? uploadFile.name : "Click or drag video file here"}
                    </p>
                    <p className="text-[10px] text-zinc-500 mt-1">MP4, MOV, WebM</p>
                  </div>
                </div>

                <div className="p-3 bg-indigo-500/5 border border-indigo-500/10 rounded-xl text-xs text-zinc-400 flex items-start gap-2.5">
                  <Sparkles className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span>
                    Transcribes speech via faster-whisper and detects top highlight timestamps automatically.
                  </span>
                </div>

                <button
                  type="submit"
                  disabled={uploading || !uploadFile}
                  className="w-full mt-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50 text-white font-medium text-sm py-2.5 px-4 rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg shadow-indigo-600/20 cursor-pointer"
                >
                  {uploading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Uploading & Analyzing...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4" />
                      Upload & Auto-Clip
                    </>
                  )}
                </button>
              </form>
            </div>

            <div className="lg:col-span-2 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold text-white flex items-center gap-2">
                  <Film className="w-4 h-4 text-indigo-400" />
                  Your Projects ({projects.length})
                </h2>
                <button
                  onClick={fetchProjects}
                  className="text-xs text-zinc-400 hover:text-white flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Refresh
                </button>
              </div>

              {projects.length === 0 ? (
                <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-2xl p-12 text-center flex flex-col items-center justify-center gap-3">
                  <Film className="w-10 h-10 text-zinc-600" />
                  <p className="text-sm font-medium text-zinc-400">No video projects yet</p>
                  <p className="text-xs text-zinc-500 max-w-sm">
                    Upload your first video to start automated transcript generation and 9:16 short clip extraction.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {projects.map((proj) => (
                    <div
                      key={proj.id}
                      onClick={() => setSelectedProjectId(proj.id)}
                      className="bg-zinc-900/60 hover:bg-zinc-900 border border-zinc-800 hover:border-zinc-700 rounded-xl p-5 cursor-pointer transition-all flex flex-col justify-between group shadow-lg"
                    >
                      <div className="flex flex-col gap-2">
                        <div className="flex items-center justify-between">
                          <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full ${
                            proj.status === "ready" 
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : proj.status === "analyzing"
                              ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse"
                              : "bg-zinc-800 text-zinc-400"
                          }`}>
                            {proj.status}
                          </span>
                          <span className="text-xs text-zinc-500 flex items-center gap-1">
                            <Clock className="w-3 h-3" /> {Math.round(proj.duration)}s
                          </span>
                        </div>
                        <h3 className="font-semibold text-sm text-zinc-100 group-hover:text-indigo-300 transition-colors">
                          {proj.name}
                        </h3>
                      </div>

                      <div className="mt-4 pt-3 border-t border-zinc-800/60 flex items-center justify-between text-xs text-zinc-400">
                        <span>{proj.clips_count} candidate clips</span>
                        <span className="text-indigo-400 flex items-center gap-1 font-medium group-hover:translate-x-0.5 transition-transform">
                          Open Studio <ChevronRight className="w-3.5 h-3.5" />
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          projectDetails && (
            <div className="flex flex-col gap-6">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-zinc-900/80 border border-zinc-800 rounded-2xl p-6">
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => setSelectedProjectId(null)}
                    className="p-2 hover:bg-zinc-800 rounded-xl text-zinc-400 hover:text-white transition-colors cursor-pointer"
                  >
                    <ArrowLeft className="w-5 h-5" />
                  </button>
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-lg font-bold text-white">{projectDetails.name}</h2>
                      <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full ${
                        projectDetails.status === "ready" 
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse"
                      }`}>
                        {projectDetails.status}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-400 mt-1">
                      Duration: {Math.round(projectDetails.duration)}s • Resolution: {projectDetails.width}x{projectDetails.height} ({projectDetails.fps} fps)
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={() => fetchProjectDetails(projectDetails.id)}
                    className="text-xs px-3.5 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-xl flex items-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <RefreshCw className="w-3.5 h-3.5" /> Refresh Status
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-1 bg-zinc-900/60 border border-zinc-800 rounded-2xl p-5 flex flex-col gap-4 max-h-[750px]">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <FileText className="w-4 h-4 text-indigo-400" />
                    Speech Transcript
                  </h3>
                  <div className="flex-1 overflow-y-auto space-y-3 pr-2">
                    {projectDetails.transcript && projectDetails.transcript.segments.length > 0 ? (
                      projectDetails.transcript.segments.map((seg) => (
                        <div key={seg.id} className="p-3 bg-zinc-950/60 border border-zinc-800/80 rounded-xl text-xs space-y-1">
                          <div className="flex items-center justify-between text-[10px] text-indigo-400 font-mono">
                            <span>{seg.start.toFixed(1)}s - {seg.end.toFixed(1)}s</span>
                          </div>
                          <p className="text-zinc-300 leading-relaxed">{seg.text}</p>
                        </div>
                      ))
                    ) : (
                      <div className="p-8 text-center text-xs text-zinc-500">
                        {projectDetails.status === "analyzing" 
                          ? "Transcribing audio via faster-whisper..."
                          : "No speech segments detected."}
                      </div>
                    )}
                  </div>
                </div>

                <div className="lg:col-span-2 flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-violet-400" />
                      AI Highlight Clips ({projectDetails.clips.length})
                    </h3>
                  </div>

                  {projectDetails.clips.length === 0 ? (
                    <div className="bg-zinc-900/40 border border-zinc-800 rounded-2xl p-12 text-center text-xs text-zinc-500">
                      {projectDetails.status === "analyzing"
                        ? "Generating highlight candidates from transcript & timing..."
                        : "No candidate clips generated."}
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {projectDetails.clips.map((clip) => {
                        const ratio = aspectRatios[clip.id] || "9:16";
                        const isRendering = renderingClips[clip.id] || clip.status === "rendering" || clip.status === "queued";

                        return (
                          <div
                            key={clip.id}
                            className="bg-zinc-900/80 border border-zinc-800 rounded-2xl p-5 flex flex-col justify-between gap-4 shadow-xl"
                          >
                            <div className="space-y-3">
                              <div className="flex items-center justify-between">
                                <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-violet-500/10 text-violet-400 border border-violet-500/20">
                                  Hook Score: {clip.score}%
                                </span>
                                <span className="text-xs text-zinc-400 font-mono">
                                  {clip.start_time}s - {clip.end_time}s ({clip.duration}s)
                                </span>
                              </div>

                              <h4 className="font-semibold text-sm text-zinc-100">
                                {clip.title}
                              </h4>

                              <div className="flex items-center gap-2 pt-2">
                                <span className="text-[11px] text-zinc-400">Ratio:</span>
                                {["9:16", "1:1", "16:9"].map((r) => (
                                  <button
                                    key={r}
                                    onClick={() => setAspectRatios(prev => ({ ...prev, [clip.id]: r }))}
                                    className={`text-[10px] px-2.5 py-1 rounded-lg border transition-all cursor-pointer ${
                                      ratio === r 
                                        ? "bg-indigo-600 text-white border-indigo-500 font-semibold"
                                        : "bg-zinc-950 text-zinc-400 border-zinc-800 hover:border-zinc-700"
                                    }`}
                                  >
                                    {r}
                                  </button>
                                ))}
                              </div>

                              {clip.has_output && (
                                <div className="mt-2 rounded-xl overflow-hidden border border-zinc-800 bg-black aspect-[9/16] max-h-56 mx-auto">
                                  <video
                                    src={`${API_BASE}/api/v1/clips/${clip.id}/stream`}
                                    controls
                                    className="w-full h-full object-contain"
                                  />
                                </div>
                              )}
                            </div>

                            <div className="pt-3 border-t border-zinc-800/80 flex items-center justify-between gap-2">
                              {clip.has_output ? (
                                <a
                                  href={`${API_BASE}/api/v1/clips/${clip.id}/download`}
                                  className="w-full bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold py-2 px-3 rounded-xl flex items-center justify-center gap-2 transition-colors cursor-pointer"
                                >
                                  <Download className="w-3.5 h-3.5" /> Download {clip.aspect_ratio} Video
                                </a>
                              ) : (
                                <button
                                  onClick={() => handleRenderClip(clip.id)}
                                  disabled={isRendering}
                                  className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold py-2 px-3 rounded-xl flex items-center justify-center gap-2 transition-colors cursor-pointer"
                                >
                                  {isRendering ? (
                                    <>
                                      <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Rendering {ratio}...
                                    </>
                                  ) : (
                                    <>
                                      <Play className="w-3.5 h-3.5" /> Render {ratio} Clip
                                    </>
                                  )}
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        )}
      </main>
    </div>
  );
}

