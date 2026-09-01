def calculate_score(correct_answers, total_questions):
    if total_questions == 0:
        return 0

    return round((correct_answers / total_questions) * 100, 2)


def calculate_mastery(
    accuracy,
    response_time_score,
    behavior_score,
    difficulty_score
):
    mastery = (
        accuracy * 0.50 +
        response_time_score * 0.15 +
        behavior_score * 0.15 +
        difficulty_score * 0.20
    )

    return round(mastery, 2)


def get_mastery_level(mastery):
    if mastery >= 80:
        return "Mastered"
    elif mastery >= 60:
        return "Developing"
    elif mastery >= 40:
        return "Weak"
    else:
        return "Critical"