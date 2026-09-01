import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Learning Dashboard")

learner_model = st.session_state.get(
    "learner_model"
)

if learner_model is None:

    st.info(
        "Complete an assessment to generate your learner dashboard."
    )

    st.stop()


st.metric(
    "Overall Mastery",
    f"{learner_model['overall_mastery']:.1f}%"
)

st.metric(
    "Learning Level",
    learner_model["overall_level"]
)


mastery_data = []

for name, data in learner_model[
    "concept_mastery"
].items():

    mastery_data.append(
        {
            "Concept":
                name.replace(
                    "_",
                    " "
                ).title(),

            "Mastery":
                float(
                    data["mastery"]
                )
        }
    )


fig = px.bar(
    mastery_data,
    x="Concept",
    y="Mastery",
    range_y=[0, 100],
    title="Concept Mastery"
)

st.plotly_chart(
    fig,
    use_container_width=True
)


weak = len(
    learner_model[
        "weak_concepts"
    ]
)

strong = len(
    learner_model[
        "strong_concepts"
    ]
)

fig2 = px.pie(

    values=[
        strong,
        weak
    ],

    names=[
        "Strong",
        "Weak"
    ],

    hole=0.5,

    title="Learning Status"
)

st.plotly_chart(
    fig2,
    use_container_width=True
)