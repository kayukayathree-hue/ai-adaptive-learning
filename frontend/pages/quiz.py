import streamlit as st

st.set_page_config(
    page_title="Quiz",
    page_icon="📝"
)

st.title("📝 Quiz")

if (
    "quiz_result"
    not in st.session_state
    or
    st.session_state.quiz_result is None
):

    st.info(
        "Complete a lesson before taking the quiz."
    )

else:

    result = st.session_state.quiz_result

    st.metric(
        "Score",
        f"{result['score']} / {result['total']}"
    )

    st.metric(
        "Accuracy",
        f"{result['percentage']:.1f}%"
    )