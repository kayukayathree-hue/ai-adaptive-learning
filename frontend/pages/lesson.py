import streamlit as st

st.set_page_config(
    page_title="Lesson",
    page_icon="📚"
)

st.title("📚 Lesson")

st.write(
    "Your personalized lesson will appear here."
)

if "selected_concept" not in st.session_state:

    st.info(
        "Start a lesson from the App page."
    )

else:

    st.success(
        f"Current concept: "
        f"{st.session_state.selected_concept}"
    )