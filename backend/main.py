
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(
    title="AI Adaptive Learning API",
    version="3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-memory storage.
# Restarting FastAPI clears this data. Your existing database layer
# can still be used by Streamlit for persistent learning records.
video_tracking: Dict[str, Dict[str, Dict[str, Any]]] = {}


class VideoEvent(BaseModel):
    student: str
    concept: str
    event: str
    position: float = Field(default=0.0, ge=0.0)
    section: Optional[str] = None
    section_index: Optional[int] = None
    from_position: Optional[float] = Field(default=None, ge=0.0)


def create_tracking() -> Dict[str, Any]:
    return {
        "play_count": 0,
        "pause_count": 0,
        "progress_count": 0,
        "seek_count": 0,
        "revisit_count": 0,
        "completion_count": 0,
        "last_position": 0.0,
        "watch_time": 0.0,
        "last_event": None,
        "last_event_time": None,
        "sections": {},
    }


def create_section_tracking() -> Dict[str, Any]:
    return {
        "play_count": 0,
        "pause_count": 0,
        "progress_count": 0,
        "seek_count": 0,
        "revisit_count": 0,
        "completion_count": 0,
        "watch_time": 0.0,
        "last_position": 0.0,
        "difficulty_score": 0.0,
    }


def normalize_section_data(section_data):
    """
    Normalize common sections.json structures.

    Supported:
      [...]
      {"sections": [...]}
      {"data": [...]}
    """
    if isinstance(section_data, list):
        return section_data

    if isinstance(section_data, dict):
        if isinstance(section_data.get("sections"), list):
            return section_data["sections"]

        if isinstance(section_data.get("data"), list):
            return section_data["data"]

    return []


def safe_float(value, default=0.0):
    try:
        number = float(value)
        if number != number:
            return default
        return number
    except (TypeError, ValueError):
        return default


def calculate_difficulty(section_tracking):
    score = (
        section_tracking.get("revisit_count", 0) * 20
        + section_tracking.get("pause_count", 0) * 10
        + section_tracking.get("seek_count", 0) * 8
    )

    return round(min(100.0, float(score)), 1)


@app.get("/")
def root():
    return {
        "message": "FastAPI connection successful",
        "tracking": "enabled",
        "version": "3.0",
    }


@app.get("/test")
def test():
    return {
        "message": "Tracking API is working",
    }


@app.post("/tracking/video")
def receive_video_event(data: VideoEvent):
    student = data.student.strip()
    concept = data.concept.strip().lower()
    event = data.event.strip().lower()

    if not student:
        return {
            "status": "error",
            "message": "Student name cannot be empty.",
        }

    if not concept:
        return {
            "status": "error",
            "message": "Concept cannot be empty.",
        }

    allowed_events = {
        "play",
        "pause",
        "progress",
        "seek",
        "revisit",
        "completed",
    }

    if event not in allowed_events:
        return {
            "status": "error",
            "message": f"Unknown video event: {event}",
        }

    position = max(
        safe_float(data.position),
        0.0,
    )

    section_name = (
        data.section.strip()
        if data.section and data.section.strip()
        else "General"
    )

    section_index = (
        data.section_index
        if data.section_index is not None
        else 0
    )

    student_data = video_tracking.setdefault(
        student,
        {},
    )

    tracking = student_data.setdefault(
        concept,
        create_tracking(),
    )

    sections = tracking.setdefault(
        "sections",
        {},
    )

    section_tracking = sections.setdefault(
        section_name,
        create_section_tracking(),
    )

    previous_position = safe_float(
        tracking.get("last_position", 0.0)
    )

    # ------------------------------------------------------------
    # EVENT COUNTERS
    # ------------------------------------------------------------

    if event == "play":
        tracking["play_count"] += 1
        section_tracking["play_count"] += 1

    elif event == "pause":
        tracking["pause_count"] += 1
        section_tracking["pause_count"] += 1

    elif event == "progress":
        tracking["progress_count"] += 1
        section_tracking["progress_count"] += 1

    elif event == "seek":
        tracking["seek_count"] += 1
        section_tracking["seek_count"] += 1

    elif event == "revisit":
        tracking["revisit_count"] += 1
        section_tracking["revisit_count"] += 1

    elif event == "completed":
        tracking["completion_count"] += 1
        section_tracking["completion_count"] += 1

    # ------------------------------------------------------------
    # WATCH TIME
    # ------------------------------------------------------------
    #
    # Only "progress" events contribute to watch time.
    # The browser sends these once per second while the video is
    # actually playing.
    #
    # This prevents:
    #   - pause events from adding watch time
    #   - seeks from adding watch time
    #   - backward revisits from adding watch time
    #   - huge browser jumps from adding fake watch time
    # ------------------------------------------------------------

    if event == "progress":
        position_difference = position - previous_position

        if 0 < position_difference <= 3:
            tracking["watch_time"] += position_difference
            section_tracking["watch_time"] += position_difference

    # ------------------------------------------------------------
    # POSITION
    # ------------------------------------------------------------

    tracking["last_position"] = position
    section_tracking["last_position"] = position

    # ------------------------------------------------------------
    # METADATA
    # ------------------------------------------------------------

    now = datetime.now(timezone.utc).isoformat()

    tracking["last_event"] = event
    tracking["last_event_time"] = now

    section_tracking["difficulty_score"] = calculate_difficulty(
        section_tracking
    )

    # ------------------------------------------------------------
    # LOG
    # ------------------------------------------------------------

    print()
    print("=" * 72)
    print("VIDEO EVENT RECEIVED")
    print("=" * 72)
    print("Time       :", now)
    print("Student    :", student)
    print("Concept    :", concept)
    print("Event      :", event)
    print("Position   :", round(position, 2))
    print("Section    :", section_name)
    print("Section ID :", section_index)

    if data.from_position is not None:
        print(
            "From Pos   :",
            round(float(data.from_position), 2),
        )

    print()
    print("GLOBAL TRACKING")
    print("Play       :", tracking["play_count"])
    print("Pause      :", tracking["pause_count"])
    print("Progress   :", tracking["progress_count"])
    print("Seek       :", tracking["seek_count"])
    print("Revisit    :", tracking["revisit_count"])
    print("Completed  :", tracking["completion_count"])
    print("Watch Time :", round(tracking["watch_time"], 2))

    print()
    print("SECTION TRACKING")
    print("Section    :", section_name)
    print("Play       :", section_tracking["play_count"])
    print("Pause      :", section_tracking["pause_count"])
    print("Progress   :", section_tracking["progress_count"])
    print("Seek       :", section_tracking["seek_count"])
    print("Revisit    :", section_tracking["revisit_count"])
    print("Watch Time :", round(section_tracking["watch_time"], 2))
    print("Difficulty :", section_tracking["difficulty_score"])
    print("=" * 72)
    print()

    return {
        "status": "success",
        "student": student,
        "concept": concept,
        "event": event,
        "position": position,
        "section": section_name,
        "section_index": section_index,
        "tracking": tracking,
    }


@app.get("/tracking/video/{student}/{concept}")
def get_video_tracking(student: str, concept: str):
    student = student.strip()
    concept = concept.strip().lower()

    tracking = (
        video_tracking
        .get(student, {})
        .get(concept)
    )

    if tracking is None:
        tracking = create_tracking()

    return {
        "student": student,
        "concept": concept,
        "tracking": tracking,
        "sections": tracking.get("sections", {}),
    }
