from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_required
)

from extensions import db

from models.patient import Patient
from models.project import Project

patients_bp = Blueprint(
    "patients",
    __name__
)


# ====================================
# ADD PATIENT
# ====================================

@patients_bp.route(
    "/patient/add/<int:project_id>",
    methods=["GET", "POST"]
)
@login_required
def add_patient(project_id):

    project = Project.query.get_or_404(
        project_id
    )

    if request.method == "POST":

        patient = Patient(

            project_id=project.id,

            patient_name=request.form.get(
                "patient_name"
            ),

            aadhaar=request.form.get(
                "aadhaar"
            ),

            age=request.form.get(
                "age"
            ),

            phone=request.form.get(
                "phone"
            ),

            address=request.form.get(
                "address"
            ),

            blood_group=request.form.get(
                "blood_group"
            ),

            weight=request.form.get(
                "weight"
            ),

            risk_status=request.form.get(
                "risk_status"
            )
        )

        db.session.add(patient)
        db.session.commit()

        flash(
            "Patient Added Successfully",
            "success"
        )

        return redirect(
            url_for(
                "dashboard.view_project",
                project_id=project.id
            )
        )

    return render_template(
        "patient.html",
        project=project
    )


# ====================================
# VIEW PATIENT PROFILE
# ====================================

@patients_bp.route(
    "/patient/<int:patient_id>"
)
@login_required
def view_patient(patient_id):

    patient = Patient.query.get_or_404(
        patient_id
    )

    return render_template(
        "profile.html",
        patient=patient
    )


# ====================================
# SEARCH PATIENT
# ====================================

@patients_bp.route(
    "/patient/search",
    methods=["GET", "POST"]
)
@login_required
def search_patient():

    patient = None

    if request.method == "POST":

        aadhaar = request.form.get(
            "aadhaar"
        )

        patient = Patient.query.filter_by(
            aadhaar=aadhaar
        ).first()

        if not patient:

            flash(
                "Patient Not Found",
                "danger"
            )

    return render_template(
        "search_patient.html",
        patient=patient
    )


# ====================================
# EDIT PATIENT
# ====================================

@patients_bp.route(
    "/patient/edit/<int:patient_id>",
    methods=["GET", "POST"]
)
@login_required
def edit_patient(patient_id):

    patient = Patient.query.get_or_404(
        patient_id
    )

    if request.method == "POST":

        patient.patient_name = request.form.get(
            "patient_name"
        )

        patient.age = request.form.get(
            "age"
        )

        patient.phone = request.form.get(
            "phone"
        )

        patient.address = request.form.get(
            "address"
        )

        patient.weight = request.form.get(
            "weight"
        )

        patient.blood_group = request.form.get(
            "blood_group"
        )

        patient.risk_status = request.form.get(
            "risk_status"
        )

        db.session.commit()

        flash(
            "Patient Updated Successfully",
            "success"
        )

        return redirect(
            url_for(
                "patients.view_patient",
                patient_id=patient.id
            )
        )

    return render_template(
        "edit_patient.html",
        patient=patient
    )


# ====================================
# DELETE PATIENT
# ====================================

@patients_bp.route(
    "/patient/delete/<int:patient_id>"
)
@login_required
def delete_patient(patient_id):

    patient = Patient.query.get_or_404(
        patient_id
    )

    project_id = patient.project_id

    db.session.delete(patient)

    db.session.commit()

    flash(
        "Patient Deleted Successfully",
        "success"
    )

    return redirect(
        url_for(
            "dashboard.view_project",
            project_id=project_id
        )
    )


# ====================================
# LIST ALL PATIENTS
# ====================================

@patients_bp.route(
    "/patients"
)
@login_required
def all_patients():

    patients = Patient.query.order_by(
        Patient.created_at.desc()
    ).all()

    return render_template(
        "all_patients.html",
        patients=patients
    )