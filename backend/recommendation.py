PREREQUISITES = {

    "logistic_regression": [
        "classification_basics",
        "categorical_variables"
    ],

    "linear_regression_types": [
        "regression_basics",
        "dependent_variable"
    ],

    "regression_prediction": [
        "regression_basics",
        "independent_variables"
    ],

    "classification_examples": [
        "classification_basics"
    ],

    "image_classification": [
        "classification_basics"
    ],

    "classification_prediction": [
        "classification_basics"
    ]

}


TEACHING_METHODS = {

    "low": [
        "Simple explanation",
        "Real-world analogy",
        "Step-by-step example"
    ],

    "medium": [
        "Visual explanation",
        "Worked example",
        "Analogy"
    ],

    "high": [
        "Technical explanation",
        "Problem solving",
        "Application-based example"
    ]

}


def recommend_learning_path(
    learner_model
):

    recommendations = []

    weak_concepts = learner_model[
        "weak_concepts"
    ]

    mastery = learner_model[
        "concept_mastery"
    ]


    for concept in weak_concepts:

        current_mastery = mastery[
            concept
        ]["mastery"]


        prerequisites = PREREQUISITES.get(
            concept,
            []
        )


        if current_mastery < 40:

            level = "low"

        elif current_mastery < 70:

            level = "medium"

        else:

            level = "high"


        recommendations.append({

            "weak_concept":
                concept,

            "mastery":
                current_mastery,

            "recommended_prerequisites":
                prerequisites,

            "teaching_methods":
                TEACHING_METHODS[level],

            "reason":
                "Low mastery detected in this concept."

        })


    return recommendations