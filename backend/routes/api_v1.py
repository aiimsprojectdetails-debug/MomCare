from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user, login_user
from werkzeug.security import generate_password_hash
from models.user import User
from models.patient import Patient
from models.project import Project
from extensions import db
from datetime import datetime

# Create API v1 blueprint
api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


def _clean_text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def serialize_user(user):
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "name": user.full_name,
        "role": user.role
    }


def serialize_patient(patient):
    return {
        "id": patient.id,
        "project_id": patient.project_id,
        "name": patient.patient_name,
        "patient_name": patient.patient_name,
        "age": patient.age,
        "aadhaar": patient.aadhaar,
        "mobile": patient.phone,
        "phone": patient.phone,
        "address": patient.address,
        "blood_group": patient.blood_group,
        "weight": patient.weight,
        "risk_status": patient.risk_status,
        
        # A. Identification
        "registration_date": patient.registration_date.isoformat() if patient.registration_date else None,
        
        # B. Socio-demographic
        "education": patient.education,
        "occupation": patient.occupation,
        "family_type": patient.family_type,
        
        # C. Obstetric History
        "gravida": patient.gravida,
        "para": patient.para,
        "abortions": patient.abortions,
        "stillbirth": patient.stillbirth,
        "preterm_birth": patient.preterm_birth,
        "cesarean": patient.cesarean,
        
        # D. Medical History
        "hypertension": patient.hypertension,
        "diabetes": patient.diabetes,
        "thyroid": patient.thyroid,
        "anemia": patient.anemia,
        "other_disease": patient.other_disease,
        
        # E. Current Pregnancy
        "lmp": patient.lmp.isoformat() if patient.lmp else None,
        "edd": patient.edd.isoformat() if patient.edd else None,
        "gestational_age": patient.gestational_age,
        "pregnancy_type": patient.pregnancy_type,
        
        # F. Baseline Anthropometry
        "height": patient.height,
        "bmi": patient.bmi,
        "muac": patient.muac,
        
        "created_at": patient.created_at.isoformat() if patient.created_at else None
    }


def serialize_project(project):
    return {
        "id": project.id,
        "project_name": project.project_name,
        "hospital_name": project.hospital_name,
        "description": project.description,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "patient_count": Patient.query.filter_by(project_id=project.id).count()
    }

# ========================
# AUTH ENDPOINTS
# ========================

@api_v1_bp.route("/auth/register", methods=["POST"])
def api_register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or not data.get("email") or not data.get("password") or not (data.get("full_name") or data.get("fullName")):
            return jsonify({
                "success": False,
                "message": "Missing required fields: email, password, full_name"
            }), 400
        
        email = data.get("email").strip().lower()
        password = data.get("password")
        full_name = _clean_text(data.get("full_name") or data.get("fullName"))
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({
                "success": False,
                "message": "Email already registered"
            }), 409
        
        # Create new user
        user = User(
            email=email,
            full_name=full_name,
            role=data.get("role", "doctor")
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Registration successful",
            "user": serialize_user(user)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Registration failed: {str(e)}"
        }), 500


@api_v1_bp.route("/auth/login", methods=["POST"])
def api_login():
    """Login user with email and password"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or not data.get("email") or not data.get("password"):
            return jsonify({
                "success": False,
                "message": "Missing email or password"
            }), 400
        
        email = data.get("email").strip().lower()
        password = data.get("password")
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401
        
        if not user.is_active_user:
            return jsonify({
                "success": False,
                "message": "User account is inactive"
            }), 403

        login_user(user)
        
        # Return success with user data
        return jsonify({
            "success": True,
            "message": "Login successful",
            "user": serialize_user(user)
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Login failed: {str(e)}"
        }), 500


@api_v1_bp.route("/auth/forgot-password", methods=["POST"])
def api_forgot_password():
    """Request password reset (placeholder)"""
    try:
        data = request.get_json()
        
        if not data or not data.get("email"):
            return jsonify({
                "success": False,
                "message": "Email is required"
            }), 400
        
        email = data.get("email").strip().lower()
        user = User.query.filter_by(email=email).first()
        
        # Don't reveal if email exists for security
        return jsonify({
            "success": True,
            "message": "Password reset link sent to your email (if account exists)"
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500


# ========================
# PROJECT ENDPOINTS
# ========================

@api_v1_bp.route("/projects", methods=["GET"])
def api_get_projects():
    """Get all projects"""
    try:
        projects = Project.query.order_by(Project.created_at.desc()).all()
        return jsonify({
            "success": True,
            "projects": [serialize_project(project) for project in projects]
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching projects: {str(e)}"
        }), 500


@api_v1_bp.route("/projects", methods=["POST"])
def api_create_project():
    """Create a project/hospital group"""
    try:
        data = request.get_json() or {}
        hospital_name = _clean_text(data.get("hospital_name") or data.get("hospitalName"))
        project_name = _clean_text(data.get("project_name") or data.get("projectName")) or hospital_name

        if not project_name or not hospital_name:
            return jsonify({
                "success": False,
                "message": "Hospital/clinic name is required"
            }), 400

        project = Project(
            project_name=project_name,
            hospital_name=hospital_name,
            description=_clean_text(data.get("description"))
        )

        db.session.add(project)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Project created successfully",
            "project": serialize_project(project),
            "data": serialize_project(project)
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Error creating project: {str(e)}"
        }), 500


@api_v1_bp.route("/projects/<int:project_id>", methods=["DELETE"])
def api_delete_project(project_id):
    """Delete a project and its patients"""
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({
                "success": False,
                "message": "Project not found"
            }), 404

        db.session.delete(project)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Project deleted successfully"
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Error deleting project: {str(e)}"
        }), 500


# ========================
# PATIENT ENDPOINTS
# ========================

@api_v1_bp.route("/patients", methods=["GET"])
def api_get_patients():
    """Get all patients"""
    try:
        project_id = request.args.get("project_id", type=int)
        query = Patient.query
        if project_id:
            query = query.filter_by(project_id=project_id)
        patients = query.order_by(Patient.created_at.desc()).all()
        return jsonify({
            "success": True,
            "data": [serialize_patient(p) for p in patients],
            "patients": [
                {
                    **serialize_patient(p)
                }
                for p in patients
            ]
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching patients: {str(e)}"
        }), 500


@api_v1_bp.route("/patients", methods=["POST"])
def api_create_patient():
    """Create a new patient with all details"""
    try:
        data = request.get_json()
        
        patient_name = _clean_text(data.get("name") or data.get("patient_name") or data.get("patientName"))
        aadhaar = _clean_text(data.get("aadhaar"))

        if not patient_name:
            return jsonify({
                "success": False,
                "message": "Patient name is required"
            }), 400

        if not aadhaar:
            return jsonify({
                "success": False,
                "message": "Aadhaar number is required"
            }), 400

        if Patient.query.filter_by(aadhaar=aadhaar).first():
            return jsonify({
                "success": False,
                "message": "Aadhaar already registered"
            }), 409

        project_id = data.get("project_id") or data.get("projectId")
        if not project_id:
            default_project = Project.query.first()
            if not default_project:
                default_project = Project(
                    project_name="Default Clinic",
                    hospital_name="Default Clinic",
                    description="Auto-created for frontend patient registrations"
                )
                db.session.add(default_project)
                db.session.flush()
            project_id = default_project.id
        
        # Helper to convert date string to date object
        def to_date(date_str):
            if not date_str:
                return None
            try:
                if isinstance(date_str, str):
                    return datetime.strptime(date_str, "%Y-%m-%d").date()
                return date_str
            except:
                return None
        
        # Helper to convert to int
        def to_int(val):
            if val is None or val == "":
                return None
            try:
                return int(val)
            except:
                return None
        
        # Helper to convert to float
        def to_float(val):
            if val is None or val == "":
                return None
            try:
                return float(val)
            except:
                return None
        
        patient = Patient(
            project_id=project_id,
            
            # A. Identification
            patient_name=patient_name,
            aadhaar=aadhaar,
            registration_date=to_date(data.get("registrationDate") or data.get("registration_date")),
            age=to_int(data.get("age")),
            phone=_clean_text(data.get("mobile") or data.get("phone")),
            address=_clean_text(data.get("address")),
            
            # B. Socio-demographic
            education=_clean_text(data.get("education")),
            occupation=_clean_text(data.get("occupation")),
            family_type=_clean_text(data.get("familyType") or data.get("family_type")),
            
            # C. Obstetric History
            gravida=to_int(data.get("gravida")),
            para=to_int(data.get("para")),
            abortions=to_int(data.get("abortions")),
            stillbirth=to_int(data.get("stillbirth")),
            preterm_birth=to_int(data.get("pretermBirth") or data.get("preterm_birth")),
            cesarean=to_int(data.get("cesarean")),
            
            # D. Medical History
            hypertension=_clean_text(data.get("hypertension")),
            diabetes=_clean_text(data.get("diabetes")),
            thyroid=_clean_text(data.get("thyroid")),
            anemia=_clean_text(data.get("anemia")),
            other_disease=_clean_text(data.get("otherDisease") or data.get("other_disease")),
            
            # E. Current Pregnancy
            lmp=to_date(data.get("lmp")),
            edd=to_date(data.get("edd")),
            gestational_age=to_int(data.get("gestationalAge") or data.get("gestational_age")),
            pregnancy_type=_clean_text(data.get("pregnancyType") or data.get("pregnancy_type")),
            
            # F. Baseline Anthropometry
            height=to_float(data.get("height")),
            weight=to_float(data.get("weight")),
            bmi=to_float(data.get("bmi")),
            muac=to_float(data.get("muac")),
            
            # Status
            blood_group=_clean_text(data.get("bloodGroup") or data.get("blood_group")),
            risk_status=_clean_text(data.get("riskStatus") or data.get("risk_status") or "Normal")
        )
        
        db.session.add(patient)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Patient created successfully",
            "patient": {
                **serialize_patient(patient)
            },
            "data": serialize_patient(patient)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Error creating patient: {str(e)}"
        }), 500


@api_v1_bp.route("/patients/<int:patient_id>", methods=["GET"])
def api_get_patient(patient_id):
    """Get patient details"""
    try:
        patient = Patient.query.get(patient_id)
        
        if not patient:
            return jsonify({
                "success": False,
                "message": "Patient not found"
            }), 404
        
        return jsonify({
            "success": True,
            "patient": {
                **serialize_patient(patient)
            },
            "data": serialize_patient(patient)
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching patient: {str(e)}"
        }), 500


@api_v1_bp.route("/patients/<int:patient_id>", methods=["PUT"])
def api_update_patient(patient_id):
    """Update patient details with all fields"""
    try:
        patient = Patient.query.get(patient_id)
        
        if not patient:
            return jsonify({
                "success": False,
                "message": "Patient not found"
            }), 404
        
        data = request.get_json()
        data = data or {}

        # Helper functions
        def to_date(date_str):
            if not date_str:
                return None
            try:
                if isinstance(date_str, str):
                    return datetime.strptime(date_str, "%Y-%m-%d").date()
                return date_str
            except:
                return None
        
        def to_int(val):
            if val is None or val == "":
                return None
            try:
                return int(val)
            except:
                return None
        
        def to_float(val):
            if val is None or val == "":
                return None
            try:
                return float(val)
            except:
                return None

        # Update fields - handle both snake_case and camelCase
        if "name" in data or "patient_name" in data or "patientName" in data:
            patient.patient_name = _clean_text(data.get("name") or data.get("patient_name") or data.get("patientName"))
        if "age" in data:
            patient.age = to_int(data["age"])
        if "aadhaar" in data:
            new_aadhaar = _clean_text(data["aadhaar"])
            duplicate = Patient.query.filter(Patient.aadhaar == new_aadhaar, Patient.id != patient.id).first()
            if duplicate:
                return jsonify({
                    "success": False,
                    "message": "Aadhaar already registered"
                }), 409
            patient.aadhaar = new_aadhaar
        if "registration_date" in data or "registrationDate" in data:
            patient.registration_date = to_date(data.get("registration_date") or data.get("registrationDate"))
        if "mobile" in data or "phone" in data:
            patient.phone = _clean_text(data.get("mobile") or data.get("phone"))
        if "address" in data:
            patient.address = _clean_text(data.get("address"))
        
        # B. Socio-demographic
        if "education" in data:
            patient.education = _clean_text(data["education"])
        if "occupation" in data:
            patient.occupation = _clean_text(data["occupation"])
        if "family_type" in data or "familyType" in data:
            patient.family_type = _clean_text(data.get("family_type") or data.get("familyType"))
        
        # C. Obstetric History
        if "gravida" in data:
            patient.gravida = to_int(data["gravida"])
        if "para" in data:
            patient.para = to_int(data["para"])
        if "abortions" in data:
            patient.abortions = to_int(data["abortions"])
        if "stillbirth" in data:
            patient.stillbirth = to_int(data["stillbirth"])
        if "preterm_birth" in data or "pretermBirth" in data:
            patient.preterm_birth = to_int(data.get("preterm_birth") or data.get("pretermBirth"))
        if "cesarean" in data:
            patient.cesarean = to_int(data["cesarean"])
        
        # D. Medical History
        if "hypertension" in data:
            patient.hypertension = _clean_text(data["hypertension"])
        if "diabetes" in data:
            patient.diabetes = _clean_text(data["diabetes"])
        if "thyroid" in data:
            patient.thyroid = _clean_text(data["thyroid"])
        if "anemia" in data:
            patient.anemia = _clean_text(data["anemia"])
        if "other_disease" in data or "otherDisease" in data:
            patient.other_disease = _clean_text(data.get("other_disease") or data.get("otherDisease"))
        
        # E. Current Pregnancy
        if "lmp" in data:
            patient.lmp = to_date(data["lmp"])
        if "edd" in data:
            patient.edd = to_date(data["edd"])
        if "gestational_age" in data or "gestationalAge" in data:
            patient.gestational_age = to_int(data.get("gestational_age") or data.get("gestationalAge"))
        if "pregnancy_type" in data or "pregnancyType" in data:
            patient.pregnancy_type = _clean_text(data.get("pregnancy_type") or data.get("pregnancyType"))
        
        # F. Baseline Anthropometry
        if "height" in data:
            patient.height = to_float(data["height"])
        if "weight" in data:
            patient.weight = to_float(data["weight"])
        if "bmi" in data:
            patient.bmi = to_float(data["bmi"])
        if "muac" in data:
            patient.muac = to_float(data["muac"])
        
        # Status
        if "blood_group" in data or "bloodGroup" in data:
            patient.blood_group = _clean_text(data.get("blood_group") or data.get("bloodGroup"))
        if "risk_status" in data or "riskStatus" in data:
            patient.risk_status = _clean_text(data.get("risk_status") or data.get("riskStatus"))
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Patient updated successfully",
            "patient": {
                **serialize_patient(patient)
            },
            "data": serialize_patient(patient)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Error updating patient: {str(e)}"
        }), 500


# ========================
# HEALTH CHECK
# ========================

@api_v1_bp.route("/health", methods=["GET"])
def api_health():
    """Health check endpoint"""
    return jsonify({
        "success": True,
        "message": "API is running",
        "timestamp": datetime.utcnow().isoformat()
    }), 200
