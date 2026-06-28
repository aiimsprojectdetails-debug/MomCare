from datetime import datetime
from extensions import db


class Monitoring(db.Model):

    __tablename__ = "monitoring"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.id"),
        nullable=False
    )

    trimester = db.Column(
        db.String(20),
        nullable=False
    )

    visit_date = db.Column(
        db.Date,
        nullable=False
    )

    blood_pressure = db.Column(
        db.String(20)
    )

    sugar_level = db.Column(
        db.String(20)
    )

    hemoglobin = db.Column(
        db.String(20)
    )

    weight = db.Column(
        db.Float
    )

    fetal_heart_rate = db.Column(
        db.String(20)
    )

    baby_movement = db.Column(
        db.String(50)
    )

    risk_status = db.Column(
        db.String(50),
        default="Normal"
    )

    notes = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return (
            f"<Monitoring "
            f"Patient:{self.patient_id} "
            f"Trimester:{self.trimester}>"
        )