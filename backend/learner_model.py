def calculate_mastery(score, total_questions):
    """
    Calculate mastery percentage from assessment score.
    """

    if total_questions == 0:
        return 0

    return round(
        (score / total_questions) * 100,
        2
    )


def classify_mastery(mastery):
    """
    Convert mastery percentage into a learning level.
    """

    if mastery < 40:
        return "Weak"

    elif mastery < 70:
        return "Developing"

    elif mastery < 85:
        return "Good"

    else:
        return "Mastered"


def analyze_question_results(results):
    """
    Identify strong and weak concept areas
    from individual quiz questions.
    """

    concept_stats = {}

    for result in results:

        concept = result["concept"]

        if concept not in concept_stats:

            concept_stats[concept] = {
                "correct": 0,
                "wrong": 0,
                "total": 0
            }

        concept_stats[concept]["total"] += 1

        if result["is_correct"]:
            concept_stats[concept]["correct"] += 1
        else:
            concept_stats[concept]["wrong"] += 1


    concept_analysis = {}

    for concept, stats in concept_stats.items():

        mastery = round(
            (
                stats["correct"]
                / stats["total"]
            ) * 100,
            2
        )

        concept_analysis[concept] = {

            "mastery": mastery,

            "level": classify_mastery(
                mastery
            ),

            "correct": stats["correct"],

            "wrong": stats["wrong"],

            "total": stats["total"]

        }

    return concept_analysis


def build_learner_model(
    score,
    total_questions,
    results,
    tracking
):

    overall_mastery = calculate_mastery(
        score,
        total_questions
    )

    concept_analysis = analyze_question_results(
        results
    )


    weak_concepts = []

    strong_concepts = []


    for concept, data in concept_analysis.items():

        if data["mastery"] < 70:

            weak_concepts.append(concept)

        elif data["mastery"] >= 85:

            strong_concepts.append(concept)


    learner_model = {

        "overall_mastery":
            overall_mastery,

        "overall_level":
            classify_mastery(
                overall_mastery
            ),

        "concept_mastery":
            concept_analysis,

        "weak_concepts":
            weak_concepts,

        "strong_concepts":
            strong_concepts,

        "behavior": {

            "play_count":
                tracking.get(
                    "play_count",
                    0
                ),

            "pause_count":
                tracking.get(
                    "pause_count",
                    0
                ),

            "seek_count":
                tracking.get(
                    "seek_count",
                    0
                ),

            "revisit_count":
                tracking.get(
                    "revisit_count",
                    0
                ),

            "completion_count":
                tracking.get(
                    "completion_count",
                    0
                ),

            "watch_time":
                tracking.get(
                    "watch_time",
                    0
                )

        }

    }

    return learner_model