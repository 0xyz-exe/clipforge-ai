import re
from typing import List, Dict, Any

# ponytail: heuristic scoring based on speech density and punctuation. upgrade to local Ollama / LLM topic summary when available.

def generate_candidates(
    segments: List[Dict[str, Any]],
    total_duration: float,
    min_duration: float = 10.0,
    max_duration: float = 60.0,
    target_count: int = 5
) -> List[Dict[str, Any]]:
    candidates = []

    # Case 1: Transcripts available -> analyze semantic sentence windows
    if segments:
        n = len(segments)
        for i in range(n):
            start_t = segments[i]["start"]
            current_text = []
            hook_bonus = 0.0

            # Hook bonus for strong start words
            first_text = segments[i]["text"].strip().lower()
            if any(w in first_text for w in ["why", "how", "what", "secret", "best", "jangan", "rahasia", "kenapa"]):
                hook_bonus += 20.0
            if "?" in segments[i]["text"] or "!" in segments[i]["text"]:
                hook_bonus += 15.0

            for j in range(i, n):
                end_t = segments[j]["end"]
                dur = end_t - start_t
                current_text.append(segments[j]["text"])

                if dur >= min_duration:
                    if dur > max_duration:
                        break

                    combined = " ".join(current_text)
                    word_count = len(combined.split())
                    words_per_sec = word_count / dur if dur > 0 else 0

                    # Heuristic score (0-100)
                    score = min(100.0, 50.0 + (words_per_sec * 8.0) + hook_bonus)
                    
                    # Generate concise title
                    first_words = " ".join(combined.split()[:6])
                    title = f"Clip: {first_words}..." if len(combined.split()) > 6 else f"Clip: {combined}"

                    candidates.append({
                        "start_time": round(start_t, 2),
                        "end_time": round(end_t, 2),
                        "duration": round(dur, 2),
                        "score": round(score, 1),
                        "title": title
                    })

    # Case 2: No segments or video is short -> chunk by duration
    if not candidates:
        step = max(min_duration, min(total_duration, 15.0))
        cur = 0.0
        idx = 1
        while cur + 3.0 < total_duration:
            clip_end = min(cur + step, total_duration)
            dur = clip_end - cur
            if dur >= 3.0:
                candidates.append({
                    "start_time": round(cur, 2),
                    "end_time": round(clip_end, 2),
                    "duration": round(dur, 2),
                    "score": 75.0,
                    "title": f"Highlight Part {idx}"
                })
                idx += 1
            cur += step

    # Deduplicate overlapping candidates (>70% overlap)
    candidates.sort(key=lambda x: x["score"], reverse=True)
    selected = []
    for cand in candidates:
        overlap = False
        for s in selected:
            inter_start = max(cand["start_time"], s["start_time"])
            inter_end = min(cand["end_time"], s["end_time"])
            intersection = max(0.0, inter_end - inter_start)
            if intersection > 0.7 * min(cand["duration"], s["duration"]):
                overlap = True
                break
        if not overlap:
            selected.append(cand)
        if len(selected) >= target_count:
            break

    # Sort sequentially by timestamp
    selected.sort(key=lambda x: x["start_time"])
    return selected
