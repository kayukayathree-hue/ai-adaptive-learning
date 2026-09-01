import streamlit.components.v1 as components
import os


_RELEASE = True


if not _RELEASE:

    _component_func = components.declare_component(
        "video_tracker",
        url="http://localhost:3001"
    )

else:

    parent_dir = os.path.dirname(
        os.path.abspath(__file__)
    )

    build_dir = os.path.join(
        parent_dir,
        "frontend"
    )

    _component_func = components.declare_component(
        "video_tracker",
        path=build_dir
    )


def video_tracker(video_url, concept):

    return _component_func(
        video_url=video_url,
        concept=concept,
        default={
            "play_count": 0,
            "pause_count": 0,
            "revisit_count": 0,
            "watch_time": 0,
            "completion_percentage": 0,
            "current_position": 0
        }
    )