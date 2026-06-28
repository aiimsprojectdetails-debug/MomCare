from flask import Flask
from flask_cors import CORS
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from extensions import db, login_manager, mail

# Load environment variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# -------------------------
# CREATE FLASK APP
# -------------------------

app = Flask(__name__)

# -------------------------
# ENABLE CORS
# -------------------------

CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# -------------------------
# CONFIGURATION
# -------------------------

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "momcare_secret_key_2026")

# -------------------------
# MONGODB CONNECTION (with SQLite fallback)
# -------------------------

USE_MONGODB = False
db = None
mongo_client = None

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("MONGODB_DB_NAME", "momcare_db")

# Try MongoDB Atlas first
if MONGODB_URI and "<db_password>" not in MONGODB_URI:
    try:
        mongo_client = MongoClient(
            MONGODB_URI,
            tls=True,
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=5000
        )
        mongo_client.admin.command('ping')
        db = mongo_client[DB_NAME]
        
        # Collections - using existing Atlas collections
        users_collection = db["users"]
        patients_collection = db["patients"]
        projects_collection = db["hospitals"]  # Using your 'hospitals' collection
        monitoring_collection = db["visits"]    # Using your 'visits' collection
        
        # Create indexes
        users_collection.create_index("email", unique=True)
        patients_collection.create_index("aadhaar", unique=True)
        
        USE_MONGODB = True
        print(f"Connected to MongoDB Atlas: {DB_NAME}")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        print("Falling back to SQLite...")

# SQLite fallback
if not USE_MONGODB:
    from flask_sqlalchemy import SQLAlchemy
    
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///momcare.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    db_sql = SQLAlchemy(app)
    print("Using SQLite database")

# Store database type in app config
app.config["USE_MONGODB"] = USE_MONGODB
app.config["db"] = db

# -------------------------
# GMAIL CONFIGURATION
# -------------------------

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "yourgmail@gmail.com")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "your_app_password")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER", app.config["MAIL_USERNAME"])

# -------------------------
# INITIALIZE EXTENSIONS
# -------------------------

login_manager.init_app(app)
login_manager.login_view = "auth.login"

mail.init_app(app)

# -------------------------
# USER LOADER
# -------------------------

from bson import ObjectId
from werkzeug.security import check_password_hash

class User:
    def __init__(self, user_data):
        self.id = str(user_data["_id"])
        self.email = user_data["email"]
        self.full_name = user_data["full_name"]
        self.password_hash = user_data["password_hash"]
        self.role = user_data.get("role", "doctor")
        self.is_active_user = user_data.get("is_active_user", True)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        return self.id
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_active(self):
        return self.is_active_user
    
    @property
    def is_anonymous(self):
        return False

@login_manager.user_loader
def load_user(user_id):
    if not USE_MONGODB or db is None:
        return None

    user_data = users_collection.find_one({"_id": ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

# -------------------------
# IMPORT BLUEPRINTS
# -------------------------

from routes.api_v1_mongo import api_v1_bp
from routes.auth import auth_bp

# -------------------------
# REGISTER BLUEPRINTS
# -------------------------

app.register_blueprint(api_v1_bp)
app.register_blueprint(auth_bp)

# -------------------------
# RUN APPLICATION
# -------------------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
