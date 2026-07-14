"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

from sqlalchemy import Column, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# SQLite-backed activity database
Base = declarative_base()
database_path = current_dir / "activities.db"
engine = create_engine(
    f"sqlite:///{database_path}", connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=False)
    schedule = Column(String, nullable=False)
    max_participants = Column(Integer, nullable=False)
    participants = relationship(
        "Participant",
        back_populates="activity",
        cascade="all, delete-orphan",
        order_by="Participant.id",
    )


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    email = Column(String, nullable=False)
    activity = relationship("Activity", back_populates="participants")


INITIAL_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


def serialize_activity(activity: Activity):
    return {
        "description": activity.description,
        "schedule": activity.schedule,
        "max_participants": activity.max_participants,
        "participants": [participant.email for participant in activity.participants],
    }


def initialize_database():
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        if session.execute(select(Activity.id)).first():
            return

        for name, details in INITIAL_ACTIVITIES.items():
            activity = Activity(
                name=name,
                description=details["description"],
                schedule=details["schedule"],
                max_participants=details["max_participants"],
            )
            activity.participants = [
                Participant(email=email) for email in details["participants"]
            ]
            session.add(activity)

        session.commit()


@app.on_event("startup")
def startup_event():
    initialize_database()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    with SessionLocal() as session:
        activities = session.execute(select(Activity).order_by(Activity.name)).scalars()
        return {
            activity.name: serialize_activity(activity)
            for activity in activities
        }


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    with SessionLocal() as session:
        activity = session.execute(
            select(Activity).where(Activity.name == activity_name)
        ).scalar_one_or_none()

        if activity is None:
            raise HTTPException(status_code=404, detail="Activity not found")

        if any(participant.email == email for participant in activity.participants):
            raise HTTPException(
                status_code=400,
                detail="Student is already signed up"
            )

        activity.participants.append(Participant(email=email))
        session.commit()

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    with SessionLocal() as session:
        activity = session.execute(
            select(Activity).where(Activity.name == activity_name)
        ).scalar_one_or_none()

        if activity is None:
            raise HTTPException(status_code=404, detail="Activity not found")

        participant = next(
            (
                registered_participant
                for registered_participant in activity.participants
                if registered_participant.email == email
            ),
            None,
        )

        if participant is None:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity"
            )

        session.delete(participant)
        session.commit()

    return {"message": f"Unregistered {email} from {activity_name}"}
