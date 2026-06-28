import random

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user, login_user
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from datetime import datetime, timedelta

from extensions import mail

# Create API v1 blueprint
api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Helper functions
def _clean_text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None

def to_date(date_str):
    if not date_str:
        return None
    try:
        if isinstance(date_str, str):
            return datetime.strptime(date_str, "%Y-%m-%d")
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

def get_db():
    """Get database from app context"""
    from flask import current_app
    database = current_app.config.get("db")
    if database is not None:
        return database
    return __import__("app").db


def require_db():
    database = get_db()
    if database is None:
        raise RuntimeError(
            "Database is not connected. Check MONGODB_URI in momcare_bakend/.env and restart Flask."
        )
    return database

def serialize_user(user_doc):
    return {
        "id": str(user_doc["_id"]),
        "email": user_doc["email"],
        "full_name": user_doc["full_name"],
        "name": user_doc["full_name"],
        "role": user_doc.get("role", "doctor")
    }

def serialize_patient(patient_doc):
    registration_date = patient_doc.get("registration_date").isoformat() if patient_doc.get("registration_date") else None
    lmp = patient_doc.get("lmp").isoformat() if patient_doc.get("lmp") else None
    edd = patient_doc.get("edd").isoformat() if patient_doc.get("edd") else None

    return {
        "id": str(patient_doc["_id"]),
        "_id": str(patient_doc["_id"]),
        "project_id": patient_doc.get("project_id"),
        "projectId": patient_doc.get("project_id"),
        "name": patient_doc.get("patient_name"),
        "patient_name": patient_doc.get("patient_name"),
        "patientName": patient_doc.get("patient_name"),
        "age": patient_doc.get("age"),
        "aadhaar": patient_doc.get("aadhaar"),
        "mobile": patient_doc.get("phone"),
        "phone": patient_doc.get("phone"),
        "address": patient_doc.get("address"),
        "blood_group": patient_doc.get("blood_group"),
        "bloodGroup": patient_doc.get("blood_group"),
        "weight": patient_doc.get("weight"),
        "risk_status": patient_doc.get("risk_status"),
        "riskStatus": patient_doc.get("risk_status"),
        
        # A. Identification
        "registration_date": registration_date,
        "registrationDate": registration_date,
        
        # B. Socio-demographic
        "education": patient_doc.get("education"),
        "occupation": patient_doc.get("occupation"),
        "family_type": patient_doc.get("family_type"),
        "familyType": patient_doc.get("family_type"),
        
        # C. Obstetric History
        "gravida": patient_doc.get("gravida"),
        "para": patient_doc.get("para"),
        "abortions": patient_doc.get("abortions"),
        "stillbirth": patient_doc.get("stillbirth"),
        "preterm_birth": patient_doc.get("preterm_birth"),
        "pretermBirth": patient_doc.get("preterm_birth"),
        "cesarean": patient_doc.get("cesarean"),
        
        # D. Medical History
        "hypertension": patient_doc.get("hypertension"),
        "diabetes": patient_doc.get("diabetes"),
        "thyroid": patient_doc.get("thyroid"),
        "anemia": patient_doc.get("anemia"),
        "other_disease": patient_doc.get("other_disease"),
        "otherDisease": patient_doc.get("other_disease"),
        "chronicDisease": patient_doc.get("other_disease"),
        
        # E. Current Pregnancy
        "lmp": lmp,
        "edd": edd,
        "gestational_age": patient_doc.get("gestational_age"),
        "gestationalAge": patient_doc.get("gestational_age"),
        "pregnancy_type": patient_doc.get("pregnancy_type"),
        "pregnancyType": patient_doc.get("pregnancy_type"),
        
        # F. Baseline Anthropometry
        "height": patient_doc.get("height"),
        "bmi": patient_doc.get("bmi"),
        "muac": patient_doc.get("muac"),
        
        "created_at": patient_doc.get("created_at").isoformat() if patient_doc.get("created_at") else None
    }

def serialize_project(project_doc):
    from app import db
    return {
        "id": str(project_doc["_id"]),
        "project_name": project_doc.get("project_name") or project_doc.get("hospital_name"),
        "hospital_name": project_doc.get("hospital_name"),
        "description": project_doc.get("description"),
        "owner_email": project_doc.get("owner_email"),
        "collaborators": project_doc.get("collaborators", []),
        "created_at": project_doc.get("created_at").isoformat() if project_doc.get("created_at") else None,
        "patient_count": db.patients.count_documents({"project_id": str(project_doc["_id"])})
    }

verification_requests = {}
verified_emails = set()


def _generate_otp():
    return f"{random.randint(0, 999999):06d}"


def _cleanup_expired_verification(email):
    request_data = verification_requests.get(email)
    if request_data and request_data["expires_at"] < datetime.utcnow():
        verification_requests.pop(email, None)
        verified_emails.discard(email)

# ========================
# AUTH ENDPOINTS
# ========================

@api_v1_bp.route("/auth/register", methods=["POST"])
def api_register():
    """Register a new user"""
    try:
        db = require_db()
        
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
        
        if not data.get("email_verified") and email not in verified_emails:
            return jsonify({
                "success": False,
                "message": "Please verify your email before registering"
            }), 400
        
        # Check if user already exists
        existing_user = db.users.find_one({"email": email})
        if existing_user:
            return jsonify({
                "success": False,
                "message": "Email already registered"
            }), 409
        
        # Create new user
        user_doc = {
            "email": email,
            "full_name": full_name,
            "password_hash": generate_password_hash(password),
            "role": data.get("role", "doctor"),
            "is_active_user": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = db.users.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id
        
        verified_emails.discard(email)
        verification_requests.pop(email, None)
        
        return jsonify({
            "success": True,
            "message": "Registration successful",
            "user": serialize_user(user_doc)
        }), 201
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Registration failed: {str(e)}"
        }), 500


@api_v1_bp.route("/auth/login", methods=["POST"])
def api_login():
    """Login user with email and password"""
    try:
        from app import User
        db = require_db()
        
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
        user_doc = db.users.find_one({"email": email})
        
        if not user_doc:
            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401
        
        # Check password
        if not check_password_hash(user_doc["password_hash"], password):
            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401
        
        if not user_doc.get("is_active_user", True):
            return jsonify({
                "success": False,
                "message": "User account is inactive"
            }), 403

        # Login user
        user = User(user_doc)
        login_user(user)
        
        # Return success with user data
        return jsonify({
            "success": True,
            "message": "Login successful",
            "user": serialize_user(user_doc)
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Login failed: {str(e)}"
        }), 500


@api_v1_bp.route("/auth/send-verification-otp", methods=["POST"])
def api_send_verification_otp():
    """Send a verification OTP to a new user's email."""
    try:
        db = require_db()
        data = request.get_json()
        if not data or not data.get("email"):
            return jsonify({
                "success": False,
                "message": "Email is required"
            }), 400

        email = data.get("email").strip().lower()
        if db.users.find_one({"email": email}):
            return jsonify({
                "success": False,
                "message": "Email already registered"
            }), 409

        otp = _generate_otp()
        verification_requests[email] = {
            "otp": otp,
            "expires_at": datetime.utcnow() + timedelta(minutes=10)
        }

        msg = Message(
            subject="Mom's Care Email Verification Code",
            sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
            recipients=[email],
            body=(
                f"Your Mom's Care verification code is: {otp}\n\n"
                "Enter this code on the registration page. The code expires in 10 minutes."
            )
        )
        try:
            mail.send(msg)
        except Exception as send_error:
            dev_otp = otp if current_app.config.get("DEBUG", False) else None
            if dev_otp:
                return jsonify({
                    "success": True,
                    "message": "Email is not configured. Use this development OTP to continue.",
                    "otp": dev_otp,
                    "mail_error": True
                }), 200

            return jsonify({
                "success": False,
                "message": f"Failed to send OTP: {str(send_error)}",
                "mail_error": True
            }), 500

        return jsonify({
            "success": True,
            "message": "OTP sent to email successfully"
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to send OTP: {str(e)}"
        }), 500


@api_v1_bp.route("/auth/verify-email-otp", methods=["POST"])
def api_verify_email_otp():
    """Verify the OTP code for a new user's email."""
    try:
        data = request.get_json()
        if not data or not data.get("email") or not data.get("otp"):
            return jsonify({
                "success": False,
                "message": "Email and OTP are required"
            }), 400

        email = data.get("email").strip().lower()
        otp = str(data.get("otp")).strip()

        _cleanup_expired_verification(email)
        request_data = verification_requests.get(email)

        if not request_data:
            return jsonify({
                "success": False,
                "message": "No valid OTP request found for this email"
            }), 400

        if request_data["otp"] != otp:
            return jsonify({
                "success": False,
                "message": "Invalid OTP code"
            }), 400

        verified_emails.add(email)
        verification_requests.pop(email, None)

        return jsonify({
            "success": True,
            "message": "Email verified successfully"
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"OTP verification failed: {str(e)}"
        }), 500


@api_v1_bp.route("/auth/forgot-password", methods=["POST"])
def api_forgot_password():
    """Request password reset"""
    try:
        data = request.get_json()
        
        if not data or not data.get("email"):
            return jsonify({
                "success": False,
                "message": "Email is required"
            }), 400
        
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
    """Get all hospitals/projects for a user"""
    try:
        from app import db
        
        user_email = request.args.get("user_email") or request.args.get("userEmail")
        query = {}
        if user_email:
            user_email = user_email.lower().strip()
            query = {
                "$or": [
                    {"owner_email": user_email},
                    {"collaborators": user_email},
                    {"owner_email": {"$exists": False}},
                    {"owner_email": None}
                ]
            }
            
        projects = list(db.hospitals.find(query).sort("created_at", -1))
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
    """Create a hospital/project"""
    try:
        from app import db
        
        data = request.get_json() or {}
        hospital_name = _clean_text(data.get("hospital_name") or data.get("hospitalName"))
        project_name = _clean_text(data.get("project_name") or data.get("projectName")) or hospital_name

        if not project_name or not hospital_name:
            return jsonify({
                "success": False,
                "message": "Hospital/clinic name is required"
            }), 400

        owner_email = _clean_text(data.get("owner_email") or data.get("ownerEmail"))
        if not owner_email and current_user and hasattr(current_user, "email"):
            owner_email = current_user.email
        owner_email = owner_email.lower() if owner_email else None

        project_doc = {
            "project_name": project_name,
            "hospital_name": hospital_name,
            "description": _clean_text(data.get("description")),
            "owner_email": owner_email,
            "collaborators": [],
            "created_at": datetime.utcnow()
        }

        # Insert into 'hospitals' collection
        result = db.hospitals.insert_one(project_doc)
        project_doc["_id"] = result.inserted_id

        # Save collaborators invitations
        collaborators = data.get("collaborators", [])
        if isinstance(collaborators, list):
            import secrets
            for collab_email in collaborators:
                collab_email = _clean_text(collab_email)
                if collab_email:
                    token = secrets.token_urlsafe(32)
                    invitation_doc = {
                        "email": collab_email.lower(),
                        "hospital_id": str(project_doc["_id"]),
                        "role": "staff",
                        "token": token,
                        "status": "pending",
                        "invited_by": owner_email,
                        "expires_at": datetime.utcnow().replace(hour=23, minute=59, second=59) + timedelta(days=7),
                        "created_at": datetime.utcnow()
                    }
                    db.invitations.insert_one(invitation_doc)

        return jsonify({
            "success": True,
            "message": "Project created successfully",
            "project": serialize_project(project_doc),
            "data": serialize_project(project_doc)
        }), 201
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error creating project: {str(e)}"
        }), 500


@api_v1_bp.route("/projects/<project_id>", methods=["DELETE"])
def api_delete_project(project_id):
    """Delete a hospital/project and all its patients"""
    try:
        from app import db
        
        # Check if project exists
        project = db.hospitals.find_one({"_id": ObjectId(project_id)})
        
        if not project:
            return jsonify({
                "success": False,
                "message": "Project not found"
            }), 404
        
        # Delete all patients associated with this project
        db.patients.delete_many({"project_id": project_id})
        
        # Delete the project
        db.hospitals.delete_one({"_id": ObjectId(project_id)})
        
        return jsonify({
            "success": True,
            "message": "Project and associated patients deleted successfully"
        }), 200
        
    except Exception as e:
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
        from app import db
        
        project_id = request.args.get("project_id") or request.args.get("projectId")
        query = {}
        if project_id:
            query["project_id"] = project_id
            
        patients = list(db.patients.find(query).sort("created_at", -1))
        return jsonify({
            "success": True,
            "patients": [serialize_patient(patient) for patient in patients]
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
        from app import db
        
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

        if db.patients.find_one({"aadhaar": aadhaar}):
            return jsonify({
                "success": False,
                "message": "Aadhaar already registered"
            }), 409

        project_id = data.get("project_id") or data.get("projectId")
        if not project_id:
            # Get or create default hospital
            default_project = db.hospitals.find_one({"hospital_name": "Default Clinic"})
            if not default_project:
                project_doc = {
                    "project_name": "Default Clinic",
                    "hospital_name": "Default Clinic",
                    "description": "Auto-created for frontend patient registrations",
                    "created_at": datetime.utcnow()
                }
                result = db.hospitals.insert_one(project_doc)
                project_id = str(result.inserted_id)
            else:
                project_id = str(default_project["_id"])
        
        patient_doc = {
            "project_id": project_id,
            
            # A. Identification
            "patient_name": patient_name,
            "aadhaar": aadhaar,
            "registration_date": to_date(data.get("registrationDate") or data.get("registration_date")),
            "age": to_int(data.get("age")),
            "phone": _clean_text(data.get("mobile") or data.get("phone")),
            "address": _clean_text(data.get("address")),
            
            # B. Socio-demographic
            "education": _clean_text(data.get("education")),
            "occupation": _clean_text(data.get("occupation")),
            "family_type": _clean_text(data.get("familyType") or data.get("family_type")),
            
            # C. Obstetric History
            "gravida": to_int(data.get("gravida")),
            "para": to_int(data.get("para")),
            "abortions": to_int(data.get("abortions")),
            "stillbirth": to_int(data.get("stillbirth")),
            "preterm_birth": to_int(data.get("pretermBirth") or data.get("preterm_birth")),
            "cesarean": to_int(data.get("cesarean")),
            
            # D. Medical History
            "hypertension": _clean_text(data.get("hypertension")),
            "diabetes": _clean_text(data.get("diabetes")),
            "thyroid": _clean_text(data.get("thyroid")),
            "anemia": _clean_text(data.get("anemia")),
            "other_disease": _clean_text(data.get("otherDisease") or data.get("other_disease")),
            
            # E. Current Pregnancy
            "lmp": to_date(data.get("lmp")),
            "edd": to_date(data.get("edd")),
            "gestational_age": to_int(data.get("gestationalAge") or data.get("gestational_age")),
            "pregnancy_type": _clean_text(data.get("pregnancyType") or data.get("pregnancy_type")),
            
            # F. Baseline Anthropometry
            "height": to_float(data.get("height")),
            "weight": to_float(data.get("weight")),
            "bmi": to_float(data.get("bmi")),
            "muac": to_float(data.get("muac")),
            
            # Status
            "blood_group": _clean_text(data.get("bloodGroup") or data.get("blood_group")),
            "risk_status": _clean_text(data.get("riskStatus") or data.get("risk_status") or "Normal"),
            
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = db.patients.insert_one(patient_doc)
        patient_doc["_id"] = result.inserted_id
        
        return jsonify({
            "success": True,
            "message": "Patient created successfully",
            "patient": serialize_patient(patient_doc),
            "data": serialize_patient(patient_doc)
        }), 201
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error creating patient: {str(e)}"
        }), 500


@api_v1_bp.route("/patients/<patient_id>", methods=["GET"])
def api_get_patient(patient_id):
    """Get patient details"""
    try:
        from app import db
        
        patient = db.patients.find_one({"_id": ObjectId(patient_id)})
        
        if not patient:
            return jsonify({
                "success": False,
                "message": "Patient not found"
            }), 404
        
        return jsonify({
            "success": True,
            "patient": serialize_patient(patient),
            "data": serialize_patient(patient)
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching patient: {str(e)}"
        }), 500


@api_v1_bp.route("/patients/<patient_id>", methods=["PUT"])
def api_update_patient(patient_id):
    """Update patient details with all fields"""
    try:
        from app import db
        
        patient = db.patients.find_one({"_id": ObjectId(patient_id)})
        
        if not patient:
            return jsonify({
                "success": False,
                "message": "Patient not found"
            }), 404
        
        data = request.get_json() or {}

        update_fields = {}

        # Update fields - handle both snake_case and camelCase
        if "name" in data or "patient_name" in data or "patientName" in data:
            update_fields["patient_name"] = _clean_text(data.get("name") or data.get("patient_name") or data.get("patientName"))
        if "age" in data:
            update_fields["age"] = to_int(data["age"])
        if "aadhaar" in data:
            new_aadhaar = _clean_text(data["aadhaar"])
            duplicate = db.patients.find_one({"aadhaar": new_aadhaar, "_id": {"$ne": ObjectId(patient_id)}})
            if duplicate:
                return jsonify({
                    "success": False,
                    "message": "Aadhaar already registered"
                }), 409
            update_fields["aadhaar"] = new_aadhaar
        if "registration_date" in data or "registrationDate" in data:
            update_fields["registration_date"] = to_date(data.get("registration_date") or data.get("registrationDate"))
        if "mobile" in data or "phone" in data:
            update_fields["phone"] = _clean_text(data.get("mobile") or data.get("phone"))
        if "address" in data:
            update_fields["address"] = _clean_text(data.get("address"))
        
        # B. Socio-demographic
        if "education" in data:
            update_fields["education"] = _clean_text(data["education"])
        if "occupation" in data:
            update_fields["occupation"] = _clean_text(data["occupation"])
        if "family_type" in data or "familyType" in data:
            update_fields["family_type"] = _clean_text(data.get("family_type") or data.get("familyType"))
        
        # C. Obstetric History
        if "gravida" in data:
            update_fields["gravida"] = to_int(data["gravida"])
        if "para" in data:
            update_fields["para"] = to_int(data["para"])
        if "abortions" in data:
            update_fields["abortions"] = to_int(data["abortions"])
        if "stillbirth" in data:
            update_fields["stillbirth"] = to_int(data["stillbirth"])
        if "preterm_birth" in data or "pretermBirth" in data:
            update_fields["preterm_birth"] = to_int(data.get("preterm_birth") or data.get("pretermBirth"))
        if "cesarean" in data:
            update_fields["cesarean"] = to_int(data["cesarean"])
        
        # D. Medical History
        if "hypertension" in data:
            update_fields["hypertension"] = _clean_text(data["hypertension"])
        if "diabetes" in data:
            update_fields["diabetes"] = _clean_text(data["diabetes"])
        if "thyroid" in data:
            update_fields["thyroid"] = _clean_text(data["thyroid"])
        if "anemia" in data:
            update_fields["anemia"] = _clean_text(data["anemia"])
        if "other_disease" in data or "otherDisease" in data:
            update_fields["other_disease"] = _clean_text(data.get("other_disease") or data.get("otherDisease"))
        
        # E. Current Pregnancy
        if "lmp" in data:
            update_fields["lmp"] = to_date(data["lmp"])
        if "edd" in data:
            update_fields["edd"] = to_date(data["edd"])
        if "gestational_age" in data or "gestationalAge" in data:
            update_fields["gestational_age"] = to_int(data.get("gestational_age") or data.get("gestationalAge"))
        if "pregnancy_type" in data or "pregnancyType" in data:
            update_fields["pregnancy_type"] = _clean_text(data.get("pregnancy_type") or data.get("pregnancyType"))
        
        # F. Baseline Anthropometry
        if "height" in data:
            update_fields["height"] = to_float(data["height"])
        if "weight" in data:
            update_fields["weight"] = to_float(data["weight"])
        if "bmi" in data:
            update_fields["bmi"] = to_float(data["bmi"])
        if "muac" in data:
            update_fields["muac"] = to_float(data["muac"])
        
        # Status
        if "blood_group" in data or "bloodGroup" in data:
            update_fields["blood_group"] = _clean_text(data.get("blood_group") or data.get("bloodGroup"))
        if "risk_status" in data or "riskStatus" in data:
            update_fields["risk_status"] = _clean_text(data.get("risk_status") or data.get("riskStatus"))
        
        update_fields["updated_at"] = datetime.utcnow()
        
        db.patients.update_one({"_id": ObjectId(patient_id)}, {"$set": update_fields})
        
        updated_patient = db.patients.find_one({"_id": ObjectId(patient_id)})
        
        return jsonify({
            "success": True,
            "message": "Patient updated successfully",
            "patient": serialize_patient(updated_patient),
            "data": serialize_patient(updated_patient)
        }), 200
        
    except Exception as e:
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
        "message": "API is running with MongoDB",
        "timestamp": datetime.utcnow().isoformat()
    }), 200


# ========================
# VISITS/MONITORING ENDPOINTS
# ========================

@api_v1_bp.route("/visits", methods=["GET"])
def api_get_visits():
    """Get all patient visits"""
    try:
        from app import db
        
        visits = []
        for t in [1, 2, 3]:
            col_name = f"trimmester{t}_visits"
            col_visits = list(db[col_name].find())
            visits.extend(col_visits)
            
        visits.sort(key=lambda x: x.get("visit_date") or datetime.min, reverse=True)
        return jsonify({
            "success": True,
            "visits": [serialize_visit(visit) for visit in visits]
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching visits: {str(e)}"
        }), 500


@api_v1_bp.route("/visits", methods=["POST"])
def api_create_visit():
    """Record a patient visit"""
    try:
        from app import db
        
        data = request.get_json() or {}
        
        patient_id = data.get("patient_id") or data.get("patientId")
        if not patient_id:
            return jsonify({
                "success": False,
                "message": "Patient ID is required"
            }), 400
        
        visit_doc = {
            "patient_id": patient_id,
            "trimester": to_int(data.get("trimester")),
            "visit_date": to_date(data.get("visit_date") or data.get("visitDate")) or datetime.utcnow(),
            "gestational_week": to_int(data.get("gestational_week") or data.get("gestationalWeek")),
            
            # Diet
            "breakfast": _clean_text(data.get("breakfast")),
            "mid_snack": _clean_text(data.get("mid_snack")),
            "lunch": _clean_text(data.get("lunch")),
            "evening_snack": _clean_text(data.get("evening_snack")),
            "dinner": _clean_text(data.get("dinner")),
            "folic_acid": _clean_text(data.get("folic_acid")),
            "iron_tablets": _clean_text(data.get("iron_tablets")),
            "milk_cups": to_int(data.get("milk_cups")),
            "fruits_servings": to_int(data.get("fruits_servings")),
            "water_liters": to_float(data.get("water_liters")),
            
            # Maternal assessment (Vitals)
            "weight": to_float(data.get("weight")),
            "blood_pressure": _clean_text(data.get("blood_pressure") or data.get("bloodPressure")),
            "muac": to_float(data.get("muac")),
            "pallor": _clean_text(data.get("pallor")),
            "edema": _clean_text(data.get("edema")),
            "hemoglobin": to_float(data.get("hemoglobin")),
            "blood_sugar": to_float(data.get("blood_sugar")),
            "nausea": _clean_text(data.get("nausea")),
            "pulse": to_int(data.get("pulse")),
            "temperature": to_float(data.get("temperature")),
            
            # T1 specific
            "bleeding": _clean_text(data.get("bleeding")),
            "illness": _clean_text(data.get("illness")),
            
            # T2/T3 obstetric assessment
            "fundal_height": to_float(data.get("fundal_height")),
            "fetal_movement": _clean_text(data.get("fetal_movement")),
            "fetal_heart_rate": to_int(data.get("fetal_heart_rate")),
            "fetal_presentation": _clean_text(data.get("fetal_presentation")),
            "bleeding_obs": _clean_text(data.get("bleeding_obs")),
            "illness_obs": _clean_text(data.get("illness_obs")),
            
            # T2 specific
            "anomaly_scan": _clean_text(data.get("anomaly_scan")),
            "fetal_growth": _clean_text(data.get("fetal_growth")),
            "placenta_position": _clean_text(data.get("placenta_position")),
            "amniotic_fluid": _clean_text(data.get("amniotic_fluid")),
            "gestational_diabetes": _clean_text(data.get("gestational_diabetes")),
            "anemia_t2": _clean_text(data.get("anemia_t2")),
            "hospitalization_t2": _clean_text(data.get("hospitalization_t2")),
            
            # T3 specific
            "reduced_movement": _clean_text(data.get("reduced_movement")),
            "swelling": _clean_text(data.get("swelling")),
            "severe_headache": _clean_text(data.get("severe_headache")),
            "blurred_vision": _clean_text(data.get("blurred_vision")),
            "hospitalization_t3": _clean_text(data.get("hospitalization_t3")),
            "ctg_done": _clean_text(data.get("ctg_done")),
            "ctg_result": _clean_text(data.get("ctg_result")),
            "doppler_done": _clean_text(data.get("doppler_done")),
            
            # Complaints & Observations
            "complaints": _clean_text(data.get("complaints")),
            "observations": _clean_text(data.get("observations")),
            "diagnosis": _clean_text(data.get("diagnosis")),
            "prescription": _clean_text(data.get("prescription")),
            
            # Follow-up
            "next_visit_date": to_date(data.get("next_visit_date") or data.get("nextVisitDate")),
            "notes": _clean_text(data.get("notes")),
            
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        trimester = to_int(data.get("trimester")) or 1
        collection_name = f"trimmester{trimester}_visits"
        result = db[collection_name].insert_one(visit_doc)
        visit_doc["_id"] = result.inserted_id
        
        return jsonify({
            "success": True,
            "message": "Visit recorded successfully",
            "visit": serialize_visit(visit_doc)
        }), 201
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error recording visit: {str(e)}"
        }), 500


@api_v1_bp.route("/patients/<patient_id>/visits", methods=["GET"])
def api_get_patient_visits(patient_id):
    """Get all visits for a specific patient"""
    try:
        from app import db
        
        visits = []
        for t in [1, 2, 3]:
            col_name = f"trimmester{t}_visits"
            col_visits = list(db[col_name].find({"patient_id": patient_id}))
            visits.extend(col_visits)
            
        visits.sort(key=lambda x: x.get("visit_date") or datetime.min, reverse=True)
        return jsonify({
            "success": True,
            "visits": [serialize_visit(visit) for visit in visits]
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching patient visits: {str(e)}"
        }), 500


def serialize_visit(visit_doc):
    """Serialize visit document"""
    return {
        "id": str(visit_doc["_id"]),
        "patient_id": visit_doc.get("patient_id"),
        "trimester": visit_doc.get("trimester"),
        "visit_date": visit_doc.get("visit_date").isoformat() if visit_doc.get("visit_date") else None,
        "gestational_week": visit_doc.get("gestational_week"),
        
        # Diet
        "breakfast": visit_doc.get("breakfast"),
        "mid_snack": visit_doc.get("mid_snack"),
        "lunch": visit_doc.get("lunch"),
        "evening_snack": visit_doc.get("evening_snack"),
        "dinner": visit_doc.get("dinner"),
        "folic_acid": visit_doc.get("folic_acid"),
        "iron_tablets": visit_doc.get("iron_tablets"),
        "milk_cups": visit_doc.get("milk_cups"),
        "fruits_servings": visit_doc.get("fruits_servings"),
        "water_liters": visit_doc.get("water_liters"),
        
        # Maternal assessment
        "weight": visit_doc.get("weight"),
        "blood_pressure": visit_doc.get("blood_pressure"),
        "muac": visit_doc.get("muac"),
        "pallor": visit_doc.get("pallor"),
        "edema": visit_doc.get("edema"),
        "hemoglobin": visit_doc.get("hemoglobin"),
        "blood_sugar": visit_doc.get("blood_sugar"),
        "nausea": visit_doc.get("nausea"),
        "pulse": visit_doc.get("pulse"),
        "temperature": visit_doc.get("temperature"),
        
        # T1 specific
        "bleeding": visit_doc.get("bleeding"),
        "illness": visit_doc.get("illness"),
        
        # T2/T3 obstetric
        "fundal_height": visit_doc.get("fundal_height"),
        "fetal_movement": visit_doc.get("fetal_movement"),
        "fetal_heart_rate": visit_doc.get("fetal_heart_rate"),
        "fetal_presentation": visit_doc.get("fetal_presentation"),
        "bleeding_obs": visit_doc.get("bleeding_obs"),
        "illness_obs": visit_doc.get("illness_obs"),
        
        # T2 specific
        "anomaly_scan": visit_doc.get("anomaly_scan"),
        "fetal_growth": visit_doc.get("fetal_growth"),
        "placenta_position": visit_doc.get("placenta_position"),
        "amniotic_fluid": visit_doc.get("amniotic_fluid"),
        "gestational_diabetes": visit_doc.get("gestational_diabetes"),
        "anemia_t2": visit_doc.get("anemia_t2"),
        "hospitalization_t2": visit_doc.get("hospitalization_t2"),
        
        # T3 specific
        "reduced_movement": visit_doc.get("reduced_movement"),
        "swelling": visit_doc.get("swelling"),
        "severe_headache": visit_doc.get("severe_headache"),
        "blurred_vision": visit_doc.get("blurred_vision"),
        "hospitalization_t3": visit_doc.get("hospitalization_t3"),
        "ctg_done": visit_doc.get("ctg_done"),
        "ctg_result": visit_doc.get("ctg_result"),
        "doppler_done": visit_doc.get("doppler_done"),
        
        # General
        "complaints": visit_doc.get("complaints"),
        "observations": visit_doc.get("observations"),
        "diagnosis": visit_doc.get("diagnosis"),
        "prescription": visit_doc.get("prescription"),
        "next_visit_date": visit_doc.get("next_visit_date").isoformat() if visit_doc.get("next_visit_date") else None,
        "notes": visit_doc.get("notes"),
        "created_at": visit_doc.get("created_at").isoformat() if visit_doc.get("created_at") else None
    }


# ========================
# INVITATIONS ENDPOINTS
# ========================

@api_v1_bp.route("/invitations", methods=["GET"])
def api_get_invitations():
    """Get all invitations"""
    try:
        from app import db
        
        invitations = list(db.invitations.find().sort("created_at", -1))
        return jsonify({
            "success": True,
            "invitations": [serialize_invitation(inv) for inv in invitations]
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching invitations: {str(e)}"
        }), 500


@api_v1_bp.route("/invitations", methods=["POST"])
def api_create_invitation():
    """Create an invitation for hospital staff"""
    try:
        from app import db
        
        data = request.get_json() or {}
        
        email = _clean_text(data.get("email"))
        hospital_id = data.get("hospital_id") or data.get("hospitalId")
        
        if not email:
            return jsonify({
                "success": False,
                "message": "Email is required"
            }), 400
        
        if not hospital_id:
            return jsonify({
                "success": False,
                "message": "Hospital ID is required"
            }), 400
        
        # Generate invitation token
        import secrets
        token = secrets.token_urlsafe(32)
        
        invited_by = _clean_text(data.get("invited_by") or data.get("invitedBy"))

        invitation_doc = {
            "email": email.lower(),
            "hospital_id": hospital_id,
            "role": _clean_text(data.get("role", "staff")),
            "token": token,
            "status": "pending",
            "invited_by": invited_by.lower() if invited_by else None,
            "expires_at": datetime.utcnow().replace(hour=23, minute=59, second=59) + timedelta(days=7),
            "created_at": datetime.utcnow()
        }
        
        result = db.invitations.insert_one(invitation_doc)
        invitation_doc["_id"] = result.inserted_id
        
        return jsonify({
            "success": True,
            "message": "Invitation sent successfully",
            "invitation": serialize_invitation(invitation_doc)
        }), 201
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error creating invitation: {str(e)}"
        }), 500


def serialize_invitation(inv_doc):
    """Serialize invitation document"""
    return {
        "id": str(inv_doc["_id"]),
        "email": inv_doc.get("email"),
        "hospital_id": inv_doc.get("hospital_id"),
        "role": inv_doc.get("role"),
        "token": inv_doc.get("token"),
        "status": inv_doc.get("status"),
        "invited_by": inv_doc.get("invited_by"),
        "expires_at": inv_doc.get("expires_at").isoformat() if inv_doc.get("expires_at") else None,
        "created_at": inv_doc.get("created_at").isoformat() if inv_doc.get("created_at") else None
    }


def enrich_invitation(inv_doc):
    """Attach hospital details used by collaboration dashboards."""
    from app import db

    serialized = serialize_invitation(inv_doc)
    hospital_name = "Unknown Hospital"
    hospital_id = inv_doc.get("hospital_id")
    if hospital_id:
        try:
            hospital = db.hospitals.find_one({"_id": ObjectId(hospital_id)})
        except Exception:
            hospital = None
        if hospital:
            hospital_name = hospital.get("hospital_name") or hospital.get("project_name") or hospital_name

    serialized["hospital_name"] = hospital_name
    return serialized


# ========================
# DELIVERY ENDPOINTS
# ========================

@api_v1_bp.route("/delivery", methods=["POST"])
def api_create_delivery():
    """Record delivery outcome"""
    try:
        from app import db
        
        data = request.get_json() or {}
        
        patient_id = data.get("patient_id") or data.get("patientId")
        if not patient_id:
            return jsonify({
                "success": False,
                "message": "Patient ID is required"
            }), 400
        
        delivery_doc = {
            "patient_id": patient_id,
            
            # Maternal outcome
            "delivery_date": to_date(data.get("delivery_date") or data.get("deliveryDate")),
            "gestational_age_delivery": to_int(data.get("gestational_age_delivery") or data.get("gestAgeDelivery")),
            "mode_of_delivery": _clean_text(data.get("mode_of_delivery") or data.get("modeDelivery")),
            "maternal_complications": _clean_text(data.get("maternal_complications") or data.get("maternalComplications")),
            
            # Baby outcome
            "baby_gender": _clean_text(data.get("baby_gender") or data.get("babyGender")),
            "birth_weight": to_float(data.get("birth_weight") or data.get("birthWeight")),
            "apgar_score": to_int(data.get("apgar_score") or data.get("apgarScore")),
            "birth_status": _clean_text(data.get("birth_status") or data.get("birthStatus")),
            "nicu_admission": _clean_text(data.get("nicu_admission") or data.get("nicuAdmission")),
            "nicu_reason": _clean_text(data.get("nicu_reason") or data.get("nicuReason")),
            "baby_complications": _clean_text(data.get("baby_complications") or data.get("babyComplications")),
            "clinical_notes": _clean_text(data.get("clinical_notes") or data.get("clinicalNotes")),
            
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = db.delivery.insert_one(delivery_doc)
        delivery_doc["_id"] = result.inserted_id
        
        return jsonify({
            "success": True,
            "message": "Delivery record saved successfully",
            "delivery": serialize_delivery(delivery_doc)
        }), 201
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error saving delivery record: {str(e)}"
        }), 500


@api_v1_bp.route("/patients/<patient_id>/delivery", methods=["GET"])
def api_get_patient_delivery(patient_id):
    """Get delivery record for a specific patient"""
    try:
        from app import db
        
        delivery = db.delivery.find_one({"patient_id": patient_id})
        
        if not delivery:
            return jsonify({
                "success": True,
                "delivery": None,
                "message": "No delivery record found"
            }), 200
        
        return jsonify({
            "success": True,
            "delivery": serialize_delivery(delivery)
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching delivery record: {str(e)}"
        }), 500


@api_v1_bp.route("/delivery", methods=["GET"])
def api_get_all_deliveries():
    """Get all delivery records with patient and hospital details"""
    try:
        from app import db
        
        deliveries = list(db.delivery.find().sort("created_at", -1))
        result = []
        for d in deliveries:
            patient_name = "Unknown"
            hospital_name = "Unknown"
            patient_id = d.get("patient_id")
            if patient_id:
                patient = db.patients.find_one({"_id": ObjectId(patient_id)})
                if patient:
                    patient_name = patient.get("patient_name") or "Unknown"
                    if patient.get("project_id"):
                        hospital = db.hospitals.find_one({"_id": ObjectId(patient.get("project_id"))})
                        if hospital:
                            hospital_name = hospital.get("hospital_name") or hospital.get("project_name") or "Unknown"
            
            serialized = serialize_delivery(d)
            serialized["patient_name"] = patient_name
            serialized["hospital_name"] = hospital_name
            result.append(serialized)
            
        return jsonify({
            "success": True,
            "deliveries": result
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching deliveries: {str(e)}"
        }), 500


def serialize_delivery(delivery_doc):
    """Serialize delivery document"""
    return {
        "id": str(delivery_doc["_id"]),
        "patient_id": delivery_doc.get("patient_id"),
        "delivery_date": delivery_doc.get("delivery_date").isoformat() if delivery_doc.get("delivery_date") else None,
        "gestational_age_delivery": delivery_doc.get("gestational_age_delivery"),
        "mode_of_delivery": delivery_doc.get("mode_of_delivery"),
        "maternal_complications": delivery_doc.get("maternal_complications"),
        "baby_gender": delivery_doc.get("baby_gender"),
        "birth_weight": delivery_doc.get("birth_weight"),
        "apgar_score": delivery_doc.get("apgar_score"),
        "birth_status": delivery_doc.get("birth_status"),
        "nicu_admission": delivery_doc.get("nicu_admission"),
        "nicu_reason": delivery_doc.get("nicu_reason"),
        "baby_complications": delivery_doc.get("baby_complications"),
        "clinical_notes": delivery_doc.get("clinical_notes"),
        "created_at": delivery_doc.get("created_at").isoformat() if delivery_doc.get("created_at") else None
    }


@api_v1_bp.route("/invitations/pending", methods=["GET"])
def api_get_pending_invitations():
    """Get all pending invitations for a user email"""
    try:
        from app import db
        
        email = request.args.get("email")
        if not email:
            return jsonify({
                "success": False,
                "message": "Email parameter is required"
            }), 400
            
        invitations = list(db.invitations.find({
            "email": email.lower().strip(),
            "status": "pending"
        }))
        
        return jsonify({
            "success": True,
            "invitations": [enrich_invitation(inv) for inv in invitations]
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching pending invitations: {str(e)}"
        }), 500


@api_v1_bp.route("/invitations/summary", methods=["GET"])
def api_get_invitation_summary():
    """Get received and sent collaboration invitations for one user."""
    try:
        from app import db

        email = request.args.get("email")
        if not email:
            return jsonify({
                "success": False,
                "message": "Email parameter is required"
            }), 400

        email = email.lower().strip()
        received = list(db.invitations.find({"email": email}).sort("created_at", -1))
        sent = list(db.invitations.find({"invited_by": email}).sort("created_at", -1))

        received_pending = sum(1 for inv in received if inv.get("status") == "pending")
        sent_pending = sum(1 for inv in sent if inv.get("status") == "pending")
        sent_accepted = sum(1 for inv in sent if inv.get("status") == "accepted")
        sent_declined = sum(1 for inv in sent if inv.get("status") == "declined")

        return jsonify({
            "success": True,
            "summary": {
                "received_pending": received_pending,
                "sent_pending": sent_pending,
                "sent_accepted": sent_accepted,
                "sent_declined": sent_declined,
                "sent_total": len(sent)
            },
            "received": [enrich_invitation(inv) for inv in received],
            "sent": [enrich_invitation(inv) for inv in sent]
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching invitation summary: {str(e)}"
        }), 500


@api_v1_bp.route("/invitations/<invitation_id>/accept", methods=["POST"])
def api_accept_invitation(invitation_id):
    """Accept an invitation"""
    try:
        from app import db
        
        inv = db.invitations.find_one({"_id": ObjectId(invitation_id)})
        if not inv:
            return jsonify({
                "success": False,
                "message": "Invitation not found"
            }), 404
            
        if inv.get("status") != "pending":
            return jsonify({
                "success": False,
                "message": f"Invitation is already {inv.get('status')}"
            }), 400
            
        # Update invitation status
        db.invitations.update_one(
            {"_id": ObjectId(invitation_id)},
            {"$set": {"status": "accepted", "updated_at": datetime.utcnow()}}
        )
        
        # Add collaborator to hospital
        hospital_id = inv.get("hospital_id")
        email = inv.get("email")
        db.hospitals.update_one(
            {"_id": ObjectId(hospital_id)},
            {"$addToSet": {"collaborators": email.lower()}}
        )
        
        return jsonify({
            "success": True,
            "message": "Invitation accepted successfully"
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error accepting invitation: {str(e)}"
        }), 500


@api_v1_bp.route("/invitations/<invitation_id>/decline", methods=["POST"])
def api_decline_invitation(invitation_id):
    """Decline an invitation"""
    try:
        from app import db
        
        inv = db.invitations.find_one({"_id": ObjectId(invitation_id)})
        if not inv:
            return jsonify({
                "success": False,
                "message": "Invitation not found"
            }), 404
            
        if inv.get("status") != "pending":
            return jsonify({
                "success": False,
                "message": f"Invitation is already {inv.get('status')}"
            }), 400
            
        # Update invitation status
        db.invitations.update_one(
            {"_id": ObjectId(invitation_id)},
            {"$set": {"status": "declined", "updated_at": datetime.utcnow()}}
        )
        
        return jsonify({
            "success": True,
            "message": "Invitation declined successfully"
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error declining invitation: {str(e)}"
        }), 500

