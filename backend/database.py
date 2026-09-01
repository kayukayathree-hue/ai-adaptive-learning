import os
from datetime import datetime

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://localhost:27017"
)

client = MongoClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=3000
)

db = client[
    "adaptive_learning"
]

students = db[
    "students"
]

learning_sessions = db[
    "learning_sessions"
]


def save_student_profile(
    student_name,
    concept,
    learner_model,
    recommendations,
    adaptive_result
):

    document = {

        "student_name":
            student_name,

        "concept":
            concept,

        "learner_model":
            learner_model,

        "recommendations":
            recommendations,

        "adaptive_result":
            adaptive_result,

        "updated_at":
            datetime.utcnow()
    }

    students.update_one(

        {
            "student_name":
                student_name
        },

        {
            "$set":
                document
        },

        upsert=True
    )


def save_learning_session(
    student_name,
    concept,
    quiz_result,
    tracking,
    section_analysis
):

    document = {

        "student_name":
            student_name,

        "concept":
            concept,

        "quiz_result":
            quiz_result,

        "tracking":
            tracking,

        "section_analysis":
            section_analysis,

        "created_at":
            datetime.utcnow()
    }

    learning_sessions.insert_one(
        document
    )


def get_student_profile(
    student_name
):

    return students.find_one(
        {
            "student_name":
                student_name
        }
    )