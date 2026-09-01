def analyze_sections(
    section_data,
    quiz_results
):
    """
    Connects video sections with quiz performance.
    """

    analysis = []

    concept_results = {}

    for result in quiz_results:

        concept = result.get(
            "concept",
            "unknown"
        )

        concept_results[concept] = result

    for section in section_data:

        section_id = section["id"]

        section_name = section["name"]

        behavior = section.get(
            "behavior",
            {}
        )

        quiz_result = concept_results.get(
            section_id
        )

        if quiz_result:

            correct = quiz_result.get(
                "is_correct",
                False
            )

        else:

            correct = None

        revisit_count = behavior.get(
            "revisit_count",
            0
        )

        pause_count = behavior.get(
            "pause_count",
            0
        )

        watch_time = behavior.get(
            "watch_time",
            0
        )

        difficulty_score = 0

        if revisit_count >= 2:
            difficulty_score += 30

        if pause_count >= 3:
            difficulty_score += 20

        if watch_time > 120:
            difficulty_score += 20

        if correct is False:
            difficulty_score += 30

        difficulty_score = min(
            difficulty_score,
            100
        )

        if correct is False:
            status = "weak"

        elif difficulty_score >= 50:
            status = "needs_review"

        else:
            status = "stable"

        analysis.append(
            {
                "section_id": section_id,
                "section_name": section_name,
                "revisit_count": revisit_count,
                "pause_count": pause_count,
                "watch_time": watch_time,
                "quiz_correct": correct,
                "difficulty_score": difficulty_score,
                "status": status
            }
        )

    return analysis