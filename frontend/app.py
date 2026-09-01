
import json
import os
import sys
from urllib.parse import quote

import plotly.express as px
import requests
import streamlit as st


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============================================================
# PROJECT IMPORTS
# ============================================================

from backend.learner_model import build_learner_model
from backend.recommendation import recommend_learning_path
from backend.adaptive_engine import adapt_after_assessment
from backend.ai_tutor import generate_ai_lesson
from frontend.components.video_tracker import video_tracker


# ============================================================
# OPTIONAL SECTION ANALYSIS
# ============================================================

try:
    from backend.section_analysis import analyze_sections
except ImportError:

    def analyze_sections(sections, results):
        analysis = []

        result_by_concept = {}

        for item in results or []:
            topic = item.get("concept", "unknown")
            result_by_concept[topic] = item

        for section in sections or []:
            section_name = (
                section.get("name")
                or section.get("section_name")
                or section.get("title")
                or "Unknown Section"
            )

            topic = (
                section.get("concept")
                or section.get("topic")
                or section_name
            )

            matching_result = result_by_concept.get(topic)

            is_correct = True

            if matching_result is not None:
                is_correct = bool(
                    matching_result.get(
                        "is_correct",
                        False
                    )
                )

            analysis.append(
                {
                    "section_name": section_name,
                    "concept": topic,
                    "status": (
                        "stable"
                        if is_correct
                        else "weak"
                    ),
                    "revisit_count": 0,
                    "pause_count": 0,
                    "seek_count": 0,
                    "watch_time": 0,
                    "difficulty_score": (
                        0
                        if is_correct
                        else 100
                    ),
                }
            )

        return analysis


# ============================================================
# OPTIONAL DATABASE
# ============================================================

try:
    from backend.database import (
        save_learning_session,
        save_student_profile,
    )
except ImportError:

    def save_learning_session(**kwargs):
        return None

    def save_student_profile(**kwargs):
        return None


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Adaptive Learning",
    page_icon="🎓",
    layout="wide",
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = PROJECT_ROOT

CONCEPT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "concepts.json",
)

QUIZ_FILE = os.path.join(
    BASE_DIR,
    "data",
    "quiz.json",
)

SECTION_FILE = os.path.join(
    BASE_DIR,
    "data",
    "sections.json",
)


# ============================================================
# LOAD CONCEPTS
# ============================================================

try:
    with open(
        CONCEPT_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        concepts = json.load(file)
except Exception as exc:
    st.error(
        f"Unable to load concepts.json: {exc}"
    )
    st.stop()

if not isinstance(concepts, dict):
    st.error(
        "concepts.json must contain a JSON object."
    )
    st.stop()


# ============================================================
# LOAD QUIZ
# ============================================================

def load_quiz_data():
    try:
        with open(
            QUIZ_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        return data if isinstance(data, dict) else {}

    except Exception as exc:
        st.error(
            f"Unable to load quiz.json: {exc}"
        )
        return {}


# ============================================================
# LOAD SECTIONS
# ============================================================

def load_section_data():
    try:
        with open(
            SECTION_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        return data

    except Exception:
        return {}


def get_sections_for_concept(section_data, concept_key):
    """
    Supports these common structures:

    1. {
         "regression": [...]
       }

    2. {
         "sections": [...]
       }

    3. [...]

    4. {
         "data": [...]
       }
    """

    if isinstance(section_data, list):
        return section_data

    if not isinstance(section_data, dict):
        return []

    concept_sections = section_data.get(
        concept_key
    )

    if isinstance(concept_sections, list):
        return concept_sections

    sections = section_data.get("sections")

    if isinstance(sections, dict):
        concept_sections = sections.get(
            concept_key,
            []
        )

        if isinstance(concept_sections, list):
            return concept_sections

    if isinstance(sections, list):
        return sections

    data = section_data.get("data")

    if isinstance(data, dict):
        concept_sections = data.get(
            concept_key,
            []
        )

        if isinstance(concept_sections, list):
            return concept_sections

    if isinstance(data, list):
        return data

    return []


# ============================================================
# GET VIDEO TRACKING
# ============================================================

def get_video_tracking(student, concept):
    try:
        safe_student = quote(
            str(student).strip(),
            safe="",
        )

        safe_concept = quote(
            str(concept).strip().lower(),
            safe="",
        )

        url = (
            "http://127.0.0.1:8000"
            f"/tracking/video/{safe_student}/{safe_concept}"
        )

        response = requests.get(
            url,
            timeout=3,
        )

        if response.status_code != 200:
            return None

        data = response.json()

        tracking = data.get(
            "tracking",
            data,
        )

        if not isinstance(tracking, dict):
            return {}

        # Keep compatibility with older backend response formats.
        for key in (
            "sections",
            "section_tracking",
            "section_stats",
        ):
            if (
                key in data
                and key not in tracking
            ):
                tracking[key] = data[key]

        return tracking

    except requests.exceptions.RequestException:
        return None

    except Exception:
        return None


# ============================================================
# TRACKING HELPERS
# ============================================================

def normalize_tracking_value(value, default=0):
    try:
        if value is None:
            return default

        return int(float(value))

    except (
        TypeError,
        ValueError,
    ):
        return default


def normalize_tracking_float(value, default=0.0):
    try:
        if value is None:
            return default

        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


# ============================================================
# GET SECTION TRACKING
# ============================================================

def get_section_tracking(tracking, section_name):
    tracking = tracking or {}

    containers = [
        tracking.get("sections"),
        tracking.get("section_tracking"),
        tracking.get("section_stats"),
    ]

    target = str(
        section_name
    ).strip().lower()

    for container in containers:

        if isinstance(container, dict):

            direct = container.get(
                section_name
            )

            if isinstance(direct, dict):
                return direct

            for key, value in container.items():

                if (
                    str(key).strip().lower()
                    == target
                    and isinstance(value, dict)
                ):
                    return value

        elif isinstance(container, list):

            for item in container:

                if not isinstance(item, dict):
                    continue

                candidate = (
                    item.get("section_name")
                    or item.get("name")
                    or item.get("section")
                    or item.get("title")
                )

                if (
                    candidate is not None
                    and str(candidate).strip().lower()
                    == target
                ):
                    return item

    return {}


# ============================================================
# ENRICH SECTION ANALYSIS
# ============================================================

def enrich_section_analysis(
    section_analysis,
    tracking,
    question_results,
):
    tracking = tracking or {}

    enriched = []

    for section in section_analysis or []:

        section_name = (
            section.get("section_name")
            or section.get("name")
            or section.get("title")
            or "Unknown Section"
        )

        section_data = get_section_tracking(
            tracking,
            section_name,
        )

        revisits = normalize_tracking_value(
            section_data.get(
                "revisit_count",
                section.get(
                    "revisit_count",
                    0,
                ),
            )
        )

        pauses = normalize_tracking_value(
            section_data.get(
                "pause_count",
                section.get(
                    "pause_count",
                    0,
                ),
            )
        )

        seeks = normalize_tracking_value(
            section_data.get(
                "seek_count",
                section.get(
                    "seek_count",
                    0,
                ),
            )
        )

        watch_time = normalize_tracking_float(
            section_data.get(
                "watch_time",
                section.get(
                    "watch_time",
                    0,
                ),
            )
        )

        # Compatibility with alternative key names.
        revisits = max(
            revisits,
            normalize_tracking_value(
                section_data.get(
                    "revisits",
                    0,
                )
            ),
        )

        pauses = max(
            pauses,
            normalize_tracking_value(
                section_data.get(
                    "pauses",
                    0,
                )
            ),
        )

        seeks = max(
            seeks,
            normalize_tracking_value(
                section_data.get(
                    "seeks",
                    0,
                )
            ),
        )

        watch_time = max(
            watch_time,
            normalize_tracking_float(
                section_data.get(
                    "watched_seconds",
                    0,
                )
            ),
        )

        difficulty = min(
            100,
            (
                revisits * 15
                + pauses * 10
                + seeks * 8
            ),
        )

        existing_status = section.get(
            "status",
            "stable",
        )

        if difficulty >= 60:
            status = "weak"
        elif difficulty >= 30:
            status = "needs_review"
        else:
            status = existing_status

        enriched.append(
            {
                **section,
                "section_name": section_name,
                "revisit_count": revisits,
                "pause_count": pauses,
                "seek_count": seeks,
                "watch_time": watch_time,
                "difficulty_score": difficulty,
                "status": status,
                "tracking_available": bool(section_data),
            }
        )

    return enriched


# ============================================================
# CORRECT ANSWER
# ============================================================

def get_correct_answer(question):
    options = question.get(
        "options",
        []
    )

    answer = question.get("answer")

    if not options:
        return answer

    if isinstance(answer, dict):

        if "index" in answer:
            answer = answer["index"]

        elif "text" in answer:
            answer = answer["text"]

        elif "answer" in answer:
            answer = answer["answer"]

    if isinstance(answer, int):

        # Prefer normal zero-based index.
        if 0 <= answer < len(options):
            return options[answer]

        # Also support one-based answer indexes.
        if 1 <= answer <= len(options):
            return options[answer - 1]

    if isinstance(answer, str):

        answer_clean = answer.strip()

        for option in options:

            if (
                str(option).strip().lower()
                == answer_clean.lower()
            ):
                return option

        letters = [
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
        ]

        upper_answer = answer_clean.upper()

        if upper_answer in letters:

            index = letters.index(
                upper_answer
            )

            if index < len(options):
                return options[index]

        try:
            numeric_answer = int(
                answer_clean
            )

            if (
                0 <= numeric_answer
                < len(options)
            ):
                return options[numeric_answer]

            if (
                1 <= numeric_answer
                <= len(options)
            ):
                return options[numeric_answer - 1]

        except ValueError:
            pass

    return answer


# ============================================================
# PERSONALIZED TEACHING METHOD
# ============================================================

def select_personalized_method(
    learner_model,
    tracking,
):
    learner_model = learner_model or {}
    tracking = tracking or {}

    mastery = float(
        learner_model.get(
            "overall_mastery",
            0,
        )
    )

    pause_count = int(
        tracking.get(
            "pause_count",
            0,
        )
    )

    revisit_count = int(
        tracking.get(
            "revisit_count",
            0,
        )
    )

    seek_count = int(
        tracking.get(
            "seek_count",
            0,
        )
    )

    if mastery < 40:

        if revisit_count >= 2:
            return "Real-world analogy"

        if pause_count >= 3:
            return "Step-by-step example"

        return "Simple explanation"

    if mastery < 70:

        if seek_count >= 3:
            return "Visual explanation"

        if pause_count >= 2:
            return "Worked example"

        return "Application-based example"

    if mastery >= 85:
        return "Problem solving"

    return "Technical explanation"


# ============================================================
# CONCEPT MASTERY
# ============================================================

def calculate_concept_mastery(
    questions,
    results,
):
    concept_stats = {}
    question_lookup = {}

    for index, question in enumerate(
        questions or []
    ):
        question_id = question.get(
            "id",
            index + 1,
        )

        question_lookup[question_id] = question

    for item in results or []:

        concept_name = item.get(
            "concept",
            "general",
        )

        question_id = item.get(
            "question_id"
        )

        question = question_lookup.get(
            question_id,
            {},
        )

        if concept_name not in concept_stats:

            concept_stats[concept_name] = {
                "earned": 0.0,
                "possible": 0.0,
                "correct": 0,
                "total": 0,
            }

        max_marks = question.get(
            "max_marks",
            question.get(
                "points_possible",
                question.get(
                    "weight",
                    1,
                ),
            ),
        )

        try:
            max_marks = float(max_marks)
        except (
            TypeError,
            ValueError,
        ):
            max_marks = 1.0

        max_marks = max(
            max_marks,
            0.0,
        )

        if "marks" in item:

            try:
                earned_marks = float(
                    item["marks"]
                )
            except (
                TypeError,
                ValueError,
            ):
                earned_marks = (
                    max_marks
                    if item.get(
                        "is_correct",
                        False,
                    )
                    else 0.0
                )

        elif "score" in item:

            try:
                earned_marks = float(
                    item["score"]
                )
            except (
                TypeError,
                ValueError,
            ):
                earned_marks = (
                    max_marks
                    if item.get(
                        "is_correct",
                        False,
                    )
                    else 0.0
                )

        else:

            earned_marks = (
                max_marks
                if item.get(
                    "is_correct",
                    False,
                )
                else 0.0
            )

        earned_marks = min(
            max(earned_marks, 0.0),
            max_marks,
        )

        stats = concept_stats[
            concept_name
        ]

        stats["earned"] += earned_marks
        stats["possible"] += max_marks
        stats["total"] += 1

        if item.get(
            "is_correct",
            False,
        ):
            stats["correct"] += 1

    mastery = {}

    for concept_name, stats in (
        concept_stats.items()
    ):

        possible = stats["possible"]

        if possible <= 0:
            value = 0.0
        else:
            value = (
                stats["earned"]
                / possible
            ) * 100

        value = min(
            max(value, 0.0),
            100.0,
        )

        if value < 40:
            level = "Weak"
        elif value < 70:
            level = "Developing"
        elif value < 85:
            level = "Good"
        else:
            level = "Mastered"

        mastery[concept_name] = {
            "mastery": round(value, 1),
            "level": level,
            "correct": stats["correct"],
            "total": stats["total"],
            "earned_marks": round(
                stats["earned"],
                2,
            ),
            "possible_marks": round(
                stats["possible"],
                2,
            ),
        }

    return mastery


# ============================================================
# APPLY MARK-AWARE MASTERY
# ============================================================

def apply_mark_aware_mastery(
    learner_model,
    questions,
    results,
):
    learner_model = learner_model or {}

    concept_mastery = calculate_concept_mastery(
        questions,
        results,
    )

    total_earned = sum(
        float(data.get("earned_marks", 0))
        for data in concept_mastery.values()
    )

    total_possible = sum(
        float(data.get("possible_marks", 0))
        for data in concept_mastery.values()
    )

    if total_possible > 0:
        overall_mastery = (
            total_earned
            / total_possible
        ) * 100
    else:
        overall_mastery = 0.0

    overall_mastery = round(
        min(
            max(overall_mastery, 0.0),
            100.0,
        ),
        1,
    )

    if overall_mastery < 40:
        overall_level = "Weak"
    elif overall_mastery < 70:
        overall_level = "Developing"
    elif overall_mastery < 85:
        overall_level = "Good"
    else:
        overall_level = "Mastered"

    weak_concepts = [
        name
        for name, data in concept_mastery.items()
        if float(
            data.get(
                "mastery",
                0,
            )
        ) < 40
    ]

    strong_concepts = [
        name
        for name, data in concept_mastery.items()
        if float(
            data.get(
                "mastery",
                0,
            )
        ) >= 85
    ]

    learner_model["concept_mastery"] = concept_mastery
    learner_model["overall_mastery"] = overall_mastery
    learner_model["overall_level"] = overall_level
    learner_model["weak_concepts"] = weak_concepts
    learner_model["strong_concepts"] = strong_concepts

    return learner_model


# ============================================================
# AI GENERATION
# ============================================================

def generate_ai_response(
    concept,
    teaching_method,
    learner_model,
    behavior=None,
    generation_number=1,
):
    learner_model = learner_model or {}
    behavior = behavior or {}

    weak_concepts = learner_model.get(
        "weak_concepts",
        []
    )

    weak_topic = (
        ", ".join(weak_concepts)
        if weak_concepts
        else None
    )

    mastery = float(
        learner_model.get(
            "overall_mastery",
            0,
        )
    )

    return generate_ai_lesson(
        concept=concept,
        weak_topic=weak_topic,
        teaching_method=teaching_method,
        learner_behavior=behavior,
        mastery=mastery,
        attempt_number=generation_number,
    )


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "student_name": "",
    "selected_concept": None,
    "lesson_started": False,
    "quiz_started": False,
    "quiz_submitted": False,
    "quiz_answers": {},
    "quiz_result": None,
    "learner_model": None,
    "previous_mastery": 0.0,
    "previous_strategy": None,
    "learning_gain": 0.0,
    "adaptive_result": None,
    "recommendations": [],
    "section_analysis": [],
    "database_saved": False,
    "ai_generation_count": 0,
    "ai_lesson_text": "",
    "ai_lesson_method": "",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# TEACHING METHODS
# ============================================================

TEACHING_METHODS = [
    "Simple explanation",
    "Real-world analogy",
    "Step-by-step example",
    "Visual explanation",
    "Worked example",
    "Analogy",
    "Technical explanation",
    "Problem solving",
    "Application-based example",
]


# ============================================================
# RESET LESSON STATE
# ============================================================

def reset_lesson_state():
    st.session_state.lesson_started = False
    st.session_state.selected_concept = None
    st.session_state.quiz_started = False
    st.session_state.quiz_submitted = False
    st.session_state.quiz_answers = {}
    st.session_state.quiz_result = None
    st.session_state.learner_model = None
    st.session_state.previous_mastery = 0.0
    st.session_state.previous_strategy = None
    st.session_state.learning_gain = 0.0
    st.session_state.adaptive_result = None
    st.session_state.recommendations = []
    st.session_state.section_analysis = []
    st.session_state.database_saved = False
    st.session_state.ai_generation_count = 0
    st.session_state.ai_lesson_text = ""
    st.session_state.ai_lesson_method = ""


# ============================================================
# HEADER
# ============================================================

st.title("🎓 AI Adaptive Learning System")

st.write(
    "Learn a concept, complete an assessment, "
    "and receive personalized learning recommendations."
)

st.divider()


# ============================================================
# START SCREEN
# ============================================================

if not st.session_state.lesson_started:

    st.subheader("🚀 Start Learning")

    student_name = st.text_input(
        "Enter your name",
        value=st.session_state.student_name,
    )

    concept_options = list(concepts.keys())

    if not concept_options:
        st.error(
            "No concepts are available in concepts.json."
        )
        st.stop()

    display_names = {}

    for key in concept_options:
        concept_data = concepts.get(key, {})

        if isinstance(concept_data, dict):
            display_names[key] = concept_data.get(
                "name",
                key.replace("_", " ").title(),
            )
        else:
            display_names[key] = key.replace(
                "_",
                " ",
            ).title()

    selected_key = st.selectbox(
        "Choose a concept",
        concept_options,
        format_func=lambda key: display_names.get(
            key,
            key,
        ),
    )

    if st.button(
        "Start Lesson",
        type="primary",
    ):

        if not student_name.strip():
            st.warning(
                "Please enter your name."
            )
        else:
            reset_lesson_state()

            st.session_state.student_name = (
                student_name.strip()
            )

            st.session_state.selected_concept = (
                selected_key
            )

            st.session_state.lesson_started = True

            st.rerun()


# ============================================================
# MAIN LESSON
# ============================================================

else:

    student_name = (
        st.session_state.student_name
    )

    concept_key = (
        st.session_state.selected_concept
    )

    if concept_key not in concepts:
        st.error(
            "Selected concept was not found."
        )
        reset_lesson_state()
        st.stop()

    concept = concepts[concept_key]

    if not isinstance(concept, dict):
        st.error(
            "The selected concept must be an object in concepts.json."
        )
        st.stop()

    concept_name = concept.get(
        "name",
        concept_key.replace(
            "_",
            " ",
        ).title(),
    )

    concept_description = concept.get(
        "description",
        "",
    )

    quiz_data = load_quiz_data()

    questions = quiz_data.get(
        concept_key,
        [],
    )

    if not isinstance(questions, list):
        questions = []

    # ========================================================
    # TITLE
    # ========================================================

    st.subheader(
        f"Welcome, {student_name} 👋"
    )

    st.title(concept_name)

    if concept_description:
        st.write(concept_description)

    st.divider()

    # ========================================================
    # VIDEO LESSON
    # ========================================================

    st.subheader("🎥 Basic Lesson")

    video_relative_path = concept.get(
        "video",
        "",
    )

    video_path = os.path.join(
        BASE_DIR,
        video_relative_path,
    )

    section_data = load_section_data()

    current_sections = get_sections_for_concept(
        section_data,
        concept_key,
    )

    if os.path.exists(video_path):

        video_tracker(
            video_path=video_path,
            student=student_name,
            concept=concept_key,
            sections=current_sections,
        )

    else:
        st.error(
            f"Video not found: {video_path}"
        )

        st.info(
            "Place the correct video inside the videos folder "
            "and make sure the path in concepts.json is correct."
        )

    # ========================================================
    # VIDEO ACTIVITY
    # ========================================================

    st.divider()
    st.subheader("📊 Learning Activity")

    tracking = get_video_tracking(
        student_name,
        concept_key,
    )

    if tracking is not None:

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "▶ Play Count",
                tracking.get(
                    "play_count",
                    0,
                ),
            )

        with col2:
            st.metric(
                "⏸ Pause Count",
                tracking.get(
                    "pause_count",
                    0,
                ),
            )

        with col3:
            st.metric(
                "🔄 Revisits",
                tracking.get(
                    "revisit_count",
                    0,
                ),
            )

        col4, col5, col6 = st.columns(3)

        with col4:
            st.metric(
                "⏩ Seek Events",
                tracking.get(
                    "seek_count",
                    0,
                ),
            )

        with col5:
            st.metric(
                "📡 Progress Events",
                tracking.get(
                    "progress_count",
                    0,
                ),
            )

        with col6:
            st.metric(
                "✅ Completed",
                tracking.get(
                    "completion_count",
                    0,
                ),
            )

        col7, col8 = st.columns(2)

        with col7:
            watch_time = float(
                tracking.get(
                    "watch_time",
                    0,
                )
            )

            st.metric(
                "⏱ Watch Time",
                f"{watch_time:.1f} sec",
            )

        with col8:
            position = float(
                tracking.get(
                    "last_position",
                    0,
                )
            )

            st.metric(
                "📍 Current Position",
                f"{position:.1f} sec",
            )

    else:
        st.warning(
            "Unable to connect to the tracking server. "
            "Start FastAPI on http://127.0.0.1:8000."
        )

    # ========================================================
    # ASSESSMENT
    # ========================================================

    st.divider()
    st.subheader("📝 Assessment")

    if not questions:

        st.warning(
            "No quiz questions found for this concept."
        )

    elif not st.session_state.quiz_submitted:

        st.write(
            "Answer the following questions based on the lesson."
        )

        quiz_answers = {}

        for index, question in enumerate(
            questions
        ):

            question_id = question.get(
                "id",
                index + 1,
            )

            question_text = question.get(
                "question",
                f"Question {index + 1}",
            )

            options = question.get(
                "options",
                [],
            )

            if not options:
                st.error(
                    f"Question {index + 1} has no options."
                )
                continue

            selected = st.radio(
                question_text,
                options,
                index=None,
                key=(
                    f"{concept_key}_"
                    f"question_{question_id}"
                ),
            )

            quiz_answers[question_id] = selected

        if st.button(
            "Submit Assessment",
            type="primary",
        ):

            score = 0.0
            total_possible_marks = 0.0
            question_results = []

            for index, question in enumerate(
                questions
            ):

                question_id = question.get(
                    "id",
                    index + 1,
                )

                selected_answer = quiz_answers.get(
                    question_id
                )

                correct_answer = get_correct_answer(
                    question
                )

                is_correct = (
                    selected_answer is not None
                    and str(
                        selected_answer
                    ).strip().lower()
                    == str(
                        correct_answer
                    ).strip().lower()
                )

                max_marks = question.get(
                    "max_marks",
                    question.get(
                        "points_possible",
                        question.get(
                            "weight",
                            1,
                        ),
                    ),
                )

                try:
                    max_marks = float(max_marks)
                except (
                    TypeError,
                    ValueError,
                ):
                    max_marks = 1.0

                max_marks = max(
                    max_marks,
                    0.0,
                )

                earned_marks = (
                    max_marks
                    if is_correct
                    else 0.0
                )

                score += earned_marks
                total_possible_marks += max_marks

                question_results.append(
                    {
                        "question_id": question_id,
                        "question": question.get(
                            "question",
                            "",
                        ),
                        "concept": question.get(
                            "concept",
                            concept_key,
                        ),
                        "selected": selected_answer,
                        "correct": correct_answer,
                        "is_correct": is_correct,
                        "marks": earned_marks,
                        "max_marks": max_marks,
                    }
                )

            total_questions = len(questions)

            if total_possible_marks > 0:
                percentage = (
                    score
                    / total_possible_marks
                ) * 100
            else:
                percentage = 0.0

            result = {
                "score": round(score, 2),
                "total": total_questions,
                "total_marks": round(
                    total_possible_marks,
                    2,
                ),
                "percentage": round(
                    percentage,
                    1,
                ),
                "results": question_results,
            }

            st.session_state.quiz_answers = (
                question_results
            )

            st.session_state.quiz_result = result
            st.session_state.quiz_submitted = True

            st.rerun()

    # ========================================================
    # AFTER ASSESSMENT
    # ========================================================

    else:

        result = (
            st.session_state.quiz_result
        )

        if result is None:
            st.error(
                "Assessment result is not available."
            )
            st.stop()

        # ====================================================
        # LATEST TRACKING
        # ====================================================

        tracking = get_video_tracking(
            student_name,
            concept_key,
        )

        if tracking is None:
            tracking = {}

        # ====================================================
        # BUILD LEARNER MODEL
        # ====================================================

        learner_model = build_learner_model(
            score=result["score"],
            total_questions=result["total"],
            results=result["results"],
            tracking=tracking,
        )

        learner_model = apply_mark_aware_mastery(
            learner_model,
            questions,
            result["results"],
        )

        st.session_state.learner_model = learner_model

        # ====================================================
        # MASTERY DASHBOARD
        # ====================================================

        st.divider()
        st.header("📊 Learning Dashboard")

        mastery_data = []

        for name, data in learner_model.get(
            "concept_mastery",
            {},
        ).items():

            mastery_data.append(
                {
                    "Concept": str(name).replace(
                        "_",
                        " ",
                    ).title(),
                    "Mastery": float(
                        data.get(
                            "mastery",
                            0,
                        )
                    ),
                }
            )

        if mastery_data:

            st.subheader("Concept Mastery")

            fig_mastery = px.bar(
                mastery_data,
                x="Concept",
                y="Mastery",
                range_y=[0, 100],
                text="Mastery",
            )

            fig_mastery.update_traces(
                texttemplate="%{text:.1f}%",
                textposition="outside",
            )

            st.plotly_chart(
                fig_mastery,
                use_container_width=True,
            )

        # ====================================================
        # LEARNING STATUS DONUT
        # ====================================================

        weak_count = len(
            learner_model.get(
                "weak_concepts",
                [],
            )
        )

        strong_count = len(
            learner_model.get(
                "strong_concepts",
                [],
            )
        )

        total_concepts = len(
            learner_model.get(
                "concept_mastery",
                {},
            )
        )

        other_count = max(
            total_concepts
            - weak_count
            - strong_count,
            0,
        )

        donut_data = {
            "Category": [
                "Strong",
                "Weak",
                "Other",
            ],
            "Count": [
                strong_count,
                weak_count,
                other_count,
            ],
        }

        if total_concepts > 0:

            fig_donut = px.pie(
                donut_data,
                names="Category",
                values="Count",
                hole=0.55,
                title="Learning Status",
            )

            st.plotly_chart(
                fig_donut,
                use_container_width=True,
            )

        # ====================================================
        # BEHAVIOUR
        # ====================================================

        behavior = learner_model.get(
            "behavior",
            {},
        )

        # Fall back to server tracking if learner_model does
        # not expose the behaviour fields.
        behavior = {
            "play_count": behavior.get(
                "play_count",
                tracking.get(
                    "play_count",
                    0,
                ),
            ),
            "pause_count": behavior.get(
                "pause_count",
                tracking.get(
                    "pause_count",
                    0,
                ),
            ),
            "revisit_count": behavior.get(
                "revisit_count",
                tracking.get(
                    "revisit_count",
                    0,
                ),
            ),
            "seek_count": behavior.get(
                "seek_count",
                tracking.get(
                    "seek_count",
                    0,
                ),
            ),
            "watch_time": behavior.get(
                "watch_time",
                tracking.get(
                    "watch_time",
                    0,
                ),
            ),
        }

        behavior_data = {
            "Behavior": [
                "Play",
                "Pause",
                "Revisit",
                "Seek",
            ],
            "Count": [
                behavior["play_count"],
                behavior["pause_count"],
                behavior["revisit_count"],
                behavior["seek_count"],
            ],
        }

        fig_behavior = px.bar(
            behavior_data,
            x="Behavior",
            y="Count",
            title="Learning Behaviour",
        )

        st.plotly_chart(
            fig_behavior,
            use_container_width=True,
        )

        # ====================================================
        # OVERALL MASTERY
        # ====================================================

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Overall Mastery",
                (
                    f"{float(learner_model.get('overall_mastery', 0)):.1f}%"
                ),
            )

        with col2:
            st.metric(
                "Learning Level",
                learner_model.get(
                    "overall_level",
                    "Unknown",
                ),
            )

        # ====================================================
        # CONCEPT MASTERY DETAILS
        # ====================================================

        st.write("### Concept Mastery")

        for concept_name, data in (
            learner_model.get(
                "concept_mastery",
                {},
            ).items()
        ):

            clean_name = str(
                concept_name
            ).replace(
                "_",
                " ",
            ).title()

            st.write(
                f"**{clean_name}**"
            )

            mastery_value = float(
                data.get(
                    "mastery",
                    0,
                )
            )

            st.progress(
                min(
                    max(
                        mastery_value / 100,
                        0.0,
                    ),
                    1.0,
                )
            )

            st.caption(
                f"{mastery_value:.1f}% • "
                f"{data.get('level', 'Unknown')}"
            )

        # ====================================================
        # WEAK / STRONG AREAS
        # ====================================================

        weak_concepts = learner_model.get(
            "weak_concepts",
            [],
        )

        strong_concepts = learner_model.get(
            "strong_concepts",
            [],
        )

        if weak_concepts:
            st.warning(
                "Weak areas detected: "
                + ", ".join(weak_concepts)
            )

        if strong_concepts:
            st.success(
                "Strong areas: "
                + ", ".join(strong_concepts)
            )

        # ====================================================
        # ADAPTIVE ENGINE
        # ====================================================

        previous_mastery = float(
            st.session_state.previous_mastery
        )

        current_mastery = float(
            learner_model.get(
                "overall_mastery",
                0,
            )
        )

        adaptive_result = adapt_after_assessment(
            previous_mastery=previous_mastery,
            current_mastery=current_mastery,
            previous_strategy=(
                st.session_state.previous_strategy
            ),
            behavior=behavior,
        )

        if not isinstance(
            adaptive_result,
            dict,
        ):
            adaptive_result = {}

        st.session_state.adaptive_result = (
            adaptive_result
        )

        learning_gain = float(
            adaptive_result.get(
                "learning_gain",
                current_mastery - previous_mastery,
            )
        )

        st.session_state.learning_gain = (
            learning_gain
        )

        st.session_state.previous_strategy = (
            adaptive_result.get(
                "recommended_strategy",
                "standard",
            )
        )

        st.session_state.previous_mastery = (
            current_mastery
        )

        # ====================================================
        # RECOMMENDATIONS
        # ====================================================

        recommendations = recommend_learning_path(
            learner_model
        )

        if not isinstance(
            recommendations,
            list,
        ):
            recommendations = []

        st.session_state.recommendations = (
            recommendations
        )

        # ====================================================
        # SECTION ANALYSIS
        # ====================================================

        section_analysis = analyze_sections(
            current_sections,
            result["results"],
        )

        section_analysis = enrich_section_analysis(
            section_analysis,
            tracking,
            result["results"],
        )

        if not section_analysis:
            section_analysis = []

        st.session_state.section_analysis = (
            section_analysis
        )

        # ====================================================
        # VIDEO SECTION ANALYSIS
        # ====================================================

        if section_analysis:

            st.divider()
            st.subheader(
                "🎯 Video Section Analysis"
            )

            for section in section_analysis:

                status = section.get(
                    "status",
                    "stable",
                )

                section_name = section.get(
                    "section_name",
                    "Unknown Section",
                )

                if status == "weak":

                    st.error(
                        f"❌ {section_name} - Weak"
                    )

                elif status == "needs_review":

                    st.warning(
                        f"⚠️ {section_name} - Needs Review"
                    )

                else:

                    st.success(
                        f"✅ {section_name} - Stable"
                    )

                c1, c2, c3, c4 = st.columns(4)

                with c1:
                    st.metric(
                        "Revisits",
                        section.get(
                            "revisit_count",
                            0,
                        ),
                    )

                with c2:
                    st.metric(
                        "Pauses",
                        section.get(
                            "pause_count",
                            0,
                        ),
                    )

                with c3:
                    st.metric(
                        "Seeks",
                        section.get(
                            "seek_count",
                            0,
                        ),
                    )

                with c4:
                    st.metric(
                        "Difficulty",
                        (
                            f"{section.get('difficulty_score', 0)}%"
                        ),
                    )

                st.caption(
                    "Watch time: "
                    f"{float(section.get('watch_time', 0)):.1f} seconds"
                )

        # ====================================================
        # PERSONALIZED TEACHING
        # ====================================================

        st.divider()
        st.subheader(
            "🤖 Personalized Teaching Method"
        )

        recommended_method = (
            select_personalized_method(
                learner_model,
                behavior,
            )
        )

        st.write(
            "Based on your assessment performance "
            "and video behaviour, the recommended "
            "teaching method is:"
        )

        st.info(
            f"🎯 {recommended_method}"
        )

        if st.button(
            f"Teach Me Using: {recommended_method}",
            type="primary",
            key="personalized_teaching_button",
        ):

            st.session_state.ai_generation_count += 1

            generation_number = (
                st.session_state.ai_generation_count
            )

            with st.spinner(
                f"Teaching {concept_name} "
                f"using {recommended_method}..."
            ):

                ai_result = generate_ai_response(
                    concept=concept_name,
                    teaching_method=recommended_method,
                    learner_model=learner_model,
                    behavior=behavior,
                    generation_number=generation_number,
                )

            if isinstance(
                ai_result,
                dict,
            ) and ai_result.get(
                "success",
                False,
            ):

                st.session_state.ai_lesson_text = (
                    ai_result.get(
                        "text",
                        "",
                    )
                )

                st.session_state.ai_lesson_method = (
                    recommended_method
                )

            else:

                st.session_state.ai_lesson_text = ""

                st.error(
                    (
                        ai_result.get(
                            "text",
                            "Unable to generate the lesson.",
                        )
                        if isinstance(
                            ai_result,
                            dict,
                        )
                        else "Unable to generate the lesson."
                    )
                )

        # ====================================================
        # PERSONALIZED RECOMMENDATION
        # ====================================================

        st.divider()
        st.subheader(
            "🎯 Personalized Recommendation"
        )

        if recommendations:

            for recommendation in recommendations:

                weak_concept = recommendation.get(
                    "weak_concept",
                    "Unknown",
                )

                st.error(
                    "Weak Concept: "
                    + str(
                        weak_concept
                    ).replace(
                        "_",
                        " ",
                    ).title()
                )

                st.write(
                    "Current Mastery: "
                    f"{recommendation.get('mastery', 0)}%"
                )

                prerequisites = recommendation.get(
                    "recommended_prerequisites",
                    [],
                )

                if prerequisites:

                    st.write(
                        "**Recommended Basics:**"
                    )

                    for prerequisite in prerequisites:

                        st.write(
                            "• "
                            + str(
                                prerequisite
                            ).replace(
                                "_",
                                " ",
                            ).title()
                        )

                teaching_methods = recommendation.get(
                    "teaching_methods",
                    [],
                )

                if teaching_methods:

                    st.write(
                        "**Recommended Teaching Methods:**"
                    )

                    for method in teaching_methods:

                        st.write(
                            "• "
                            + str(method)
                        )

        else:

            st.success(
                "No major weak areas detected. "
                "You can move to the next concept."
            )

        # ====================================================
        # ADAPTIVE TEACHING DECISION
        # ====================================================

        st.divider()
        st.subheader(
            "🤖 Adaptive Teaching Decision"
        )

        st.metric(
            "Learning Gain",
            f"{learning_gain:.1f}%",
        )

        gain_data = {
            "Stage": [
                "Before",
                "After",
            ],
            "Mastery": [
                previous_mastery,
                current_mastery,
            ],
        }

        fig_gain = px.line(
            gain_data,
            x="Stage",
            y="Mastery",
            markers=True,
            range_y=[0, 100],
            title="Learning Gain",
        )

        st.plotly_chart(
            fig_gain,
            use_container_width=True,
        )

        decision = adaptive_result.get(
            "decision",
            "continue",
        )

        strategy = adaptive_result.get(
            "recommended_strategy",
            "standard",
        )

        st.write(
            "**Decision:** "
            + str(
                decision
            ).replace(
                "_",
                " ",
            ).title()
        )

        st.write(
            "**Next Teaching Method:** "
            + str(
                strategy
            ).replace(
                "_",
                " ",
            ).title()
        )

        # ====================================================
        # ASSESSMENT RESULT
        # ====================================================

        st.divider()
        st.subheader(
            "📊 Assessment Result"
        )

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Score",
                (
                    f"{result['score']:.2f} / "
                    f"{result.get('total_marks', result['total'])}"
                ),
            )

        with col2:
            st.metric(
                "Accuracy",
                f"{result['percentage']:.1f}%",
            )

        # ====================================================
        # CHOOSE TEACHING METHOD
        # ====================================================

        st.divider()
        st.subheader(
            "📚 Choose Your Teaching Method"
        )

        st.write(
            "Choose a different method if you do not "
            "want to use the automatically selected one."
        )

        selected_method = st.selectbox(
            "Teaching Method",
            TEACHING_METHODS,
            key="selected_teaching_method",
        )

        if st.button(
            "🎓 Teach Me This Way",
            key="teach_selected_method",
        ):

            st.session_state.ai_generation_count += 1

            generation_number = (
                st.session_state.ai_generation_count
            )

            with st.spinner(
                f"Generating {selected_method} lesson..."
            ):

                ai_result = generate_ai_response(
                    concept=concept_name,
                    teaching_method=selected_method,
                    learner_model=learner_model,
                    behavior=behavior,
                    generation_number=generation_number,
                )

            if isinstance(
                ai_result,
                dict,
            ) and ai_result.get(
                "success",
                False,
            ):

                st.session_state.ai_lesson_text = (
                    ai_result.get(
                        "text",
                        "",
                    )
                )

                st.session_state.ai_lesson_method = (
                    selected_method
                )

            else:

                st.session_state.ai_lesson_text = ""

                st.error(
                    (
                        ai_result.get(
                            "text",
                            "Unable to generate lesson.",
                        )
                        if isinstance(
                            ai_result,
                            dict,
                        )
                        else "Unable to generate lesson."
                    )
                )

        # ====================================================
        # AI LESSON OUTPUT
        # ====================================================

        if st.session_state.ai_lesson_text:

            st.divider()
            st.subheader(
                "🤖 AI Personalized Lesson"
            )

            if st.session_state.ai_lesson_method:
                st.caption(
                    "Teaching method: "
                    + st.session_state.ai_lesson_method
                )

            st.markdown(
                st.session_state.ai_lesson_text
            )

        # ====================================================
        # DATABASE SAVE
        # ====================================================

        if not st.session_state.database_saved:

            try:

                save_learning_session(
                    student_name=student_name,
                    concept=concept_key,
                    quiz_result=result,
                    tracking=tracking,
                    section_analysis=section_analysis,
                )

                save_student_profile(
                    student_name=student_name,
                    concept=concept_key,
                    learner_model=learner_model,
                    recommendations=recommendations,
                    adaptive_result=adaptive_result,
                )

                st.session_state.database_saved = True

            except Exception as exc:

                st.warning(
                    f"Database unavailable: {exc}"
                )


# ============================================================
# CHOOSE ANOTHER CONCEPT
# ============================================================

if st.session_state.lesson_started:

    st.divider()

    if st.button(
        "🔄 Choose Another Concept"
    ):
        reset_lesson_state()
        st.rerun()
