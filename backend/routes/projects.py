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


projects_bp = Blueprint(
    "projects",
    __name__
)


# ====================================
# ALL PROJECTS
# ====================================

@projects_bp.route("/projects")
@login_required
def all_projects():

    projects = Project.query.order_by(
        Project.created_at.desc()
    ).all()

    return render_template(
        "projects.html",
        projects=projects,
        user=current_user
    )


# ====================================
# CREATE PROJECT
# ====================================

@projects_bp.route(
    "/projects/create",
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
                "projects.all_projects"
            )
        )

    return render_template(
        "create_project.html"
    )


# ====================================
# VIEW PROJECT
# ====================================

@projects_bp.route(
    "/projects/<int:project_id>"
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


# ====================================
# EDIT PROJECT
# ====================================

@projects_bp.route(
    "/projects/edit/<int:project_id>",
    methods=["GET", "POST"]
)
@login_required
def edit_project(project_id):

    project = Project.query.get_or_404(
        project_id
    )

    if request.method == "POST":

        project.project_name = request.form.get(
            "project_name"
        )

        project.hospital_name = request.form.get(
            "hospital_name"
        )

        project.description = request.form.get(
            "description"
        )

        db.session.commit()

        flash(
            "Project Updated Successfully",
            "success"
        )

        return redirect(
            url_for(
                "projects.view_project",
                project_id=project.id
            )
        )

    return render_template(
        "edit_project.html",
        project=project
    )


# ====================================
# DELETE PROJECT
# ====================================

@projects_bp.route(
    "/projects/delete/<int:project_id>"
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
            "projects.all_projects"
        )
    )


# ====================================
# SEARCH PROJECT
# ====================================

@projects_bp.route(
    "/projects/search",
    methods=["GET", "POST"]
)
@login_required
def search_project():

    projects = []

    if request.method == "POST":

        keyword = request.form.get(
            "keyword"
        )

        projects = Project.query.filter(
            Project.project_name.ilike(
                f"%{keyword}%"
            )
        ).all()

    return render_template(
        "projects.html",
        projects=projects
    )


# ====================================
# PROJECT PATIENTS
# ====================================

@projects_bp.route(
    "/projects/<int:project_id>/patients"
)
@login_required
def project_patients(project_id):

    project = Project.query.get_or_404(
        project_id
    )

    patients = Patient.query.filter_by(
        project_id=project.id
    ).all()

    return render_template(
        "project_patients.html",
        project=project,
        patients=patients
    )


# ====================================
# PROJECT STATISTICS
# ====================================

@projects_bp.route(
    "/projects/statistics"
)
@login_required
def project_statistics():

    total_projects = Project.query.count()

    total_patients = Patient.query.count()

    projects = Project.query.all()

    statistics = []

    for project in projects:

        patient_count = Patient.query.filter_by(
            project_id=project.id
        ).count()

        statistics.append(
            {
                "project_id": project.id,
                "project_name": project.project_name,
                "hospital_name": project.hospital_name,
                "patient_count": patient_count
            }
        )

    return render_template(
        "project_statistics.html",
        statistics=statistics,
        total_projects=total_projects,
        total_patients=total_patients
    )