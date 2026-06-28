from datetime import datetime
from extensions import db

class Patient(db.Model):

    __tablename__ = "patients"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id")
    )

    # ========== A. IDENTIFICATION ==========
    patient_name = db.Column(
        db.String(100),
        nullable=False
    )

    aadhaar = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )

    registration_date = db.Column(
        db.Date
    )

    age = db.Column(
        db.Integer
    )

    phone = db.Column(
        db.String(20)
    )

    address = db.Column(
        db.Text
    )

    # ========== B. SOCIO-DEMOGRAPHIC ==========
    education = db.Column(
        db.String(50)
    )

    occupation = db.Column(
        db.String(50)
    )

    family_type = db.Column(
        db.String(20)
    )

    # ========== C. OBSTETRIC HISTORY ==========
    gravida = db.Column(
        db.Integer
    )

    para = db.Column(
        db.Integer
    )

    abortions = db.Column(
        db.Integer
    )

    stillbirth = db.Column(
        db.Integer
    )

    preterm_birth = db.Column(
        db.Integer
    )

    cesarean = db.Column(
        db.Integer
    )

    # ========== D. MEDICAL HISTORY ==========
    hypertension = db.Column(
        db.String(20)
    )

    diabetes = db.Column(
        db.String(20)
    )

    thyroid = db.Column(
        db.String(20)
    )

    anemia = db.Column(
        db.String(20)
    )

    other_disease = db.Column(
        db.Text
    )

    # ========== E. CURRENT PREGNANCY ==========
    lmp = db.Column(
        db.Date
    )

    edd = db.Column(
        db.Date
    )

    gestational_age = db.Column(
        db.Integer
    )

    pregnancy_type = db.Column(
        db.String(50)
    )

    # ========== F. BASELINE ANTHROPOMETRY ==========
    height = db.Column(
        db.Float
    )

    weight = db.Column(
        db.Float
    )

    bmi = db.Column(
        db.Float
    )

    muac = db.Column(
        db.Float
    )

    # ========== STATUS & METADATA ==========
    blood_group = db.Column(
        db.String(10)
    )

    risk_status = db.Column(
        db.String(50)
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
        return f"<Patient {self.patient_name}>"