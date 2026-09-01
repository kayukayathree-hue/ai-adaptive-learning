# ============================================================
# ADAPTIVE TEACHING ENGINE
# ============================================================

TEACHING_STRATEGIES = [
    "simple_explanation",
    "real_world_analogy",
    "visual_explanation",
    "step_by_step_example",
    "practice_problem"
]


def calculate_learning_gain(
    previous_mastery,
    current_mastery
):
    """
    Calculates the change in mastery
    between two learning cycles.
    """

    gain = current_mastery - previous_mastery

    return round(gain, 2)


def select_teaching_strategy(
    mastery,
    behavior,
    previous_strategy=None,
    previous_gain=0
):
    """
    Selects a teaching strategy based on
    mastery level and previous learning performance.
    """

    # --------------------------------------------------------
    # VERY LOW MASTERY
    # --------------------------------------------------------

    if mastery < 40:

        if previous_strategy == "simple_explanation":
            return "real_world_analogy"

        elif previous_strategy == "real_world_analogy":
            return "visual_explanation"

        elif previous_strategy == "visual_explanation":
            return "step_by_step_example"

        else:
            return "simple_explanation"

    # --------------------------------------------------------
    # DEVELOPING UNDERSTANDING
    # --------------------------------------------------------

    elif mastery < 70:

        if previous_strategy == "step_by_step_example":
            return "real_world_analogy"

        elif previous_strategy == "real_world_analogy":
            return "visual_explanation"

        else:
            return "step_by_step_example"

    # --------------------------------------------------------
    # GOOD UNDERSTANDING
    # --------------------------------------------------------

    elif mastery < 85:

        return "practice_problem"

    # --------------------------------------------------------
    # HIGH MASTERY
    # --------------------------------------------------------

    else:

        return "practice_problem"


def adapt_after_assessment(
    previous_mastery,
    current_mastery,
    previous_strategy=None,
    behavior=None
):
    """
    Makes the next teaching decision after assessment.
    """

    if behavior is None:
        behavior = {}

    learning_gain = calculate_learning_gain(
        previous_mastery,
        current_mastery
    )

    # --------------------------------------------------------
    # STUDENT IMPROVED SIGNIFICANTLY
    # --------------------------------------------------------

    if learning_gain >= 10:

        decision = "continue_strategy"

        if previous_strategy is None:
            strategy = select_teaching_strategy(
                current_mastery,
                behavior
            )
        else:
            strategy = previous_strategy

    # --------------------------------------------------------
    # STUDENT IMPROVED SLIGHTLY
    # --------------------------------------------------------

    elif learning_gain > 0:

        decision = "try_different_strategy"

        strategy = select_teaching_strategy(
            current_mastery,
            behavior,
            previous_strategy,
            learning_gain
        )

    # --------------------------------------------------------
    # STUDENT DID NOT IMPROVE
    # --------------------------------------------------------

    else:

        decision = "change_strategy"

        strategy = select_teaching_strategy(
            current_mastery,
            behavior,
            previous_strategy,
            learning_gain
        )

    return {
        "previous_mastery": previous_mastery,
        "current_mastery": current_mastery,
        "learning_gain": learning_gain,
        "decision": decision,
        "recommended_strategy": strategy
    }