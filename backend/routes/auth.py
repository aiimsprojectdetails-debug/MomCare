from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from models.user import User
from extensions import db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def home():
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password")

        if not email or not password:
            flash("Email and password are required", "danger")
            return redirect(url_for("auth.login"))

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(
                url_for("dashboard.dashboard")
            )

        flash(
            "Invalid Email or Password",
            "danger"
        )

    return render_template("login.html")




@auth_bp.route("/register", methods=["GET", "POST"])
@auth_bp.route("/signup", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password")

        if not full_name or not email or not password:
            flash("Full name, email and password are required", "danger")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered", "warning")
            return redirect(url_for("auth.register"))

        user = User(
            full_name=full_name,
            email=email
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Registration Successful", "success")

        return redirect(url_for("auth.login"))

    return render_template("signup.html")


@auth_bp.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(url_for("auth.login"))

@auth_bp.route("/forgot-password")
def forgot_password():
    return render_template(
        "forgot_password.html"
    )
