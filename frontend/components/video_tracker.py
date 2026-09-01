
import base64
import json
import mimetypes
import os

import streamlit.components.v1 as components


API_URL = "https://ai-adaptive-learning-cy6u.onrender.com"


def _to_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_sections(sections):
    if not isinstance(sections, list):
        return []

    normalized = []

    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            continue

        name = (
            section.get("section_name")
            or section.get("name")
            or section.get("title")
            or section.get("section")
            or f"Section {index + 1}"
        )

        start = None
        for key in ("start_time", "start_seconds", "start", "startTime"):
            start = _to_float(section.get(key))
            if start is not None:
                break

        end = None
        for key in ("end_time", "end_seconds", "end", "endTime"):
            end = _to_float(section.get(key))
            if end is not None:
                break

        normalized.append(
            {
                "name": str(name),
                "start": start,
                "end": end,
                "index": index,
            }
        )

    return normalized


def video_tracker(video_path, student, concept, sections=None):
    """
    Embedded HTML5 video player with server-side learning analytics.

    Events:
      play, pause, progress, seek, revisit, completed

    Progress heartbeats are sent only while the video is actually playing.
    This makes watch-time tracking much more reliable than estimating watch
    time from arbitrary browser events.
    """

    if not os.path.exists(video_path):
        components.html(
            """
            <div style="
                padding:20px;
                color:#b91c1c;
                background:#fef2f2;
                border:1px solid #fecaca;
                border-radius:8px;
                font-family:Arial,sans-serif;
            ">
                Video file not found.
            </div>
            """,
            height=100,
        )
        return

    safe_sections = _normalize_sections(sections)

    try:
        with open(video_path, "rb") as video_file:
            video_base64 = base64.b64encode(video_file.read()).decode("utf-8")
    except OSError as exc:
        components.html(
            f"""
            <div style="
                padding:20px;
                color:#b91c1c;
                background:#fef2f2;
                border:1px solid #fecaca;
                border-radius:8px;
                font-family:Arial,sans-serif;
            ">
                Unable to read video: {str(exc)}
            </div>
            """,
            height=100,
        )
        return

    mime_type = mimetypes.guess_type(video_path)[0] or "video/mp4"

    student_js = json.dumps(str(student))
    concept_js = json.dumps(str(concept))
    sections_js = json.dumps(safe_sections)
    api_url_js = json.dumps(API_URL)
    mime_type_js = json.dumps(mime_type)

    html_code = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
    html, body {{
        margin: 0;
        padding: 0;
        background: white;
        font-family: Arial, sans-serif;
    }}

    #lessonVideo {{
        width: 100%;
        max-height: 520px;
        display: block;
        background: #000;
    }}

    #status {{
        box-sizing: border-box;
        padding: 9px 12px;
        font-size: 13px;
        background: #111827;
        color: #fff;
        min-height: 18px;
    }}
</style>
</head>

<body>

<video id="lessonVideo" controls preload="metadata">
    <source
        src="data:{mime_type};base64,{video_base64}"
        type="{mime_type}"
    >
    Your browser does not support this video.
</video>

<div id="status">Connecting to tracking server...</div>

<script>
const video = document.getElementById("lessonVideo");
const statusElement = document.getElementById("status");

const student = {student_js};
const concept = {concept_js};
const sections = {sections_js};
const API_URL = {api_url_js};
const MIME_TYPE = {mime_type_js};

let lastKnownPosition = 0;
let seekStartPosition = 0;
let isSeeking = false;
let isPlaying = false;
let progressTimer = null;
let lastSectionName = null;
let metadataLoaded = false;

/*
 * Keep requests in order. Browser media events can happen very quickly,
 * and unordered POST requests can otherwise corrupt the counters/positions.
 */
let eventQueue = Promise.resolve();

function setStatus(message) {{
    statusElement.textContent = message;
}}

function getCurrentSection(position) {{
    if (!sections || sections.length === 0) {{
        return {{ name: "General", index: 0 }};
    }}

    const hasCompleteTimings = sections.every(
        section =>
            section.start !== null &&
            section.end !== null &&
            Number.isFinite(Number(section.start)) &&
            Number.isFinite(Number(section.end))
    );

    if (hasCompleteTimings) {{
        for (const section of sections) {{
            const start = Number(section.start);
            const end = Number(section.end);

            if (
                position >= start &&
                (
                    position < end ||
                    section === sections[sections.length - 1]
                )
            ) {{
                return {{
                    name: section.name,
                    index: section.index
                }};
            }}
        }}
    }}

    if (video.duration && video.duration > 0) {{
        const sectionLength = video.duration / sections.length;

        let index = Math.floor(position / sectionLength);
        index = Math.max(
            0,
            Math.min(index, sections.length - 1)
        );

        return {{
            name: sections[index].name,
            index: sections[index].index
        }};
    }}

    return {{
        name: sections[0].name,
        index: sections[0].index
    }};
}}

async function sendEvent(eventName, position, extraData = {{}}) {{
    const numericPosition = Number.isFinite(Number(position))
        ? Number(position)
        : 0;

    const section = getCurrentSection(numericPosition);

    const payload = {{
        student: student,
        concept: concept,
        event: eventName,
        position: Math.max(0, numericPosition),
        section: section.name,
        section_index: section.index,
        ...extraData
    }};

    setStatus(
        eventName.toUpperCase() +
        " • " +
        section.name
    );

    try {{
        const response = await fetch(
            API_URL + "/tracking/video",
            {{
                method: "POST",
                headers: {{
                    "Content-Type": "application/json"
                }},
                body: JSON.stringify(payload),
                keepalive: true
            }}
        );

        if (!response.ok) {{
            setStatus(
                "Tracking error: HTTP " + response.status
            );
            console.error(
                "Tracking server returned:",
                response.status
            );
            return null;
        }}

        return await response.json();
    }} catch (error) {{
        setStatus("Tracking server unavailable");
        console.error("Tracking request failed:", error);
        return null;
    }}
}}

function queueEvent(eventName, position, extraData = {{}}) {{
    eventQueue = eventQueue
        .then(() => sendEvent(eventName, position, extraData))
        .catch(error => {{
            console.error("Tracking queue error:", error);
        }});

    return eventQueue;
}}

function startProgressTracking() {{
    if (progressTimer !== null) {{
        return;
    }}

    progressTimer = window.setInterval(() => {{
        if (!video.paused && !video.ended) {{
            const currentTime = Number(video.currentTime) || 0;

            queueEvent(
                "progress",
                currentTime
            );

            lastKnownPosition = currentTime;

            const currentSection = getCurrentSection(currentTime);

            if (currentSection.name !== lastSectionName) {{
                lastSectionName = currentSection.name;
                console.log(
                    "SECTION CHANGED:",
                    currentSection.name
                );
            }}
        }}
    }}, 1000);
}}

function stopProgressTracking() {{
    if (progressTimer !== null) {{
        window.clearInterval(progressTimer);
        progressTimer = null;
    }}
}}

video.addEventListener("loadedmetadata", () => {{
    metadataLoaded = true;

    const duration = Number(video.duration) || 0;

    setStatus(
        "Tracking ready • " +
        Math.round(duration) +
        " sec"
    );

    console.log("VIDEO DURATION:", duration);
    console.log("SECTIONS:", sections);
}});

video.addEventListener("play", () => {{
    isPlaying = true;

    const position = Number(video.currentTime) || 0;

    queueEvent("play", position);

    lastKnownPosition = position;
    startProgressTracking();
}});

video.addEventListener("pause", () => {{
    isPlaying = false;

    const position = Number(video.currentTime) || 0;

    queueEvent("pause", position);

    lastKnownPosition = position;
    stopProgressTracking();
}});

video.addEventListener("seeking", () => {{
    if (!isSeeking) {{
        isSeeking = true;

        /*
         * lastKnownPosition is deliberately used here instead of
         * video.currentTime because during a seek currentTime has
         * already started changing.
         */
        seekStartPosition = lastKnownPosition;

        console.log(
            "SEEK START:",
            seekStartPosition
        );
    }}
}});

video.addEventListener("seeked", () => {{
    const newPosition = Number(video.currentTime) || 0;
    const previousPosition = Number(lastKnownPosition) || 0;
    const movement = newPosition - previousPosition;

    console.log(
        "SEEKED:",
        previousPosition,
        "->",
        newPosition
    );

    if (movement < -2) {{
        queueEvent(
            "revisit",
            newPosition,
            {{
                from_position: previousPosition
            }}
        );
    }} else if (movement > 2) {{
        queueEvent(
            "seek",
            newPosition,
            {{
                from_position: previousPosition
            }}
        );
    }}

    lastKnownPosition = newPosition;
    isSeeking = false;

    if (isPlaying) {{
        startProgressTracking();
    }}
}});

video.addEventListener("timeupdate", () => {{
    if (!isSeeking) {{
        lastKnownPosition = Number(video.currentTime) || 0;
    }}
}});

video.addEventListener("ended", () => {{
    isPlaying = false;
    stopProgressTracking();

    const position = Number(video.currentTime) || 0;

    queueEvent("completed", position);

    lastKnownPosition = position;

    setStatus("COMPLETED • Video finished");
}});

window.addEventListener("beforeunload", () => {{
    stopProgressTracking();
}});

console.log("VIDEO TRACKER INITIALIZED");
console.log("Student:", student);
console.log("Concept:", concept);
console.log("Sections:", sections);
</script>

</body>
</html>
"""

    components.html(
        html_code,
        height=590,
        scrolling=False,
    )
