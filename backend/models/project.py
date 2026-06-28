from datetime import datetime
from extensions import db


class Project(db.Model):

    __tablename__ = "projects"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    project_name = db.Column(
        db.String(200),
        nullable=False
    )

    hospital_name = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    patients = db.relationship(
        "Patient",
        backref="project",
        lazy=True,
        cascade="all, delete"
    )

    def __repr__(self):
        return f"<Project {self.project_name}>"