from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_required,
    current_user
)

from extensions import db

from models.project import Project
from models.patient import Patient

dashboard_bp = Blueprint(
    "dashboard",
    __name__
)


# ==================================
# DASHBOARD HOME
# ==================================

@dashboard_bp.route("/dashboard")
@login_required
def dashboard():

    total_projects = Project.query.count()

    total_patients = Patient.query.count()

    projects = Project.query.order_by(
        Project.created_at.desc()
    ).all()

    return render_template(
        "dashboard.html",
        user=current_user,
        total_projects=total_projects,
        total_patients=total_patients,
        projects=projects
    )


# ==================================
# CREATE PROJECT
# ==================================

@dashboard_bp.route(
    "/project/create",
    methods=["GET", "POST"]
)
@login_required
def create_project():

    if request.method == "POST":

        project_name = request.form.get(
            "project_name"
        )

        hospital_name = request.form.get(
            "hospital_name"
        )

        description = request.form.get(
            "description"
        )

        project = Project(
            project_name=project_name,
            hospital_name=hospital_name,
            description=description
        )

        db.session.add(project)
        db.session.commit()

        flash(
            "Project Created Successfully",
            "success"
        )

        return redirect(
            url_for(
                "dashboard.dashboard"
            )
        )

    return render_template(
        "create_project.html"
    )


# ==================================
# VIEW SINGLE PROJECT
# ==================================

@dashboard_bp.route(
    "/project/<int:project_id>"
)
@login_required
def view_project(project_id):

    project = Project.query.get_or_404(
        project_id
    )

    patients = Patient.query.filter_by(
        project_id=project.id
    ).all()

    patient_count = len(
        patients
    )

    return render_template(
        "project_details.html",
        project=project,
        patients=patients,
        patient_count=patient_count
    )


# ==================================
# DELETE PROJECT
# ==================================

@dashboard_bp.route(
    "/project/delete/<int:project_id>"
)
@login_required
def delete_project(project_id):

    project = Project.query.get_or_404(
        project_id
    )

    Patient.query.filter_by(
        project_id=project.id
    ).delete()

    db.session.delete(project)

    db.session.commit()

    flash(
        "Project Deleted Successfully",
        "success"
    )

    return redirect(
        url_for(
            "dashboard.dashboard"
        )
    )


# ==================================
# SEARCH PROJECT
# ==================================

@dashboard_bp.route(
    "/project/search",
    methods=["POST"]
)
@login_required
def search_project():

    keyword = request.form.get(
        "keyword"
    )

    projects = Project.query.filter(
        Project.project_name.ilike(
            f"%{keyword}%"
        )
    ).all()

    return render_template(
        "dashboard.html",
        projects=projects,
        total_projects=len(projects),
        total_patients=Patient.query.count()
    )


# ==================================
# PROJECT STATISTICS
# ==================================

@dashboard_bp.route(
    "/project/statistics"
)
@login_required
def project_statistics():

    total_projects = Project.query.count()

    total_patients = Patient.query.count()

    project_data = []

    projects = Project.query.all()

    for project in projects:

        count = Patient.query.filter_by(
            project_id=project.id
        ).count()

        project_data.append(
            {
                "project_name":
                project.project_name,

                "patients":
                count
            }
        )

    return render_template(
        "statistics.html",
        total_projects=total_projects,
        total_patients=total_patients,
        project_data=project_data
    )