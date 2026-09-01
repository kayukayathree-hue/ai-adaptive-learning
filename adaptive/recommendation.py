def recommend_next_learning(
    target_concept,
    mastery,
    weak_areas,
    prerequisites
):
    recommendations = []

    if mastery < 60:
        for prerequisite in prerequisites:
            if prerequisite in weak_areas:
                recommendations.append(prerequisite)

    if not recommendations and mastery < 60:
        recommendations = prerequisites[:2]

    if mastery >= 80:
        return {
            "status": "ready_for_next_concept",
            "recommendations": []
        }

    return {
        "status": "needs_foundation",
        "recommendations": recommendations
    }