# routes/auth.py
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, bcrypt
from models import User

auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["GET", "POST"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard_page"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=remember)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.dashboard_page"))
        flash("Invalid email or password.", "error")

    return render_template("auth.html", mode="login")


@auth.route("/signup", methods=["GET", "POST"])
def signup_page():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard_page"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")

        # Validation
        if len(username) < 3:
            flash("Username must be at least 3 characters.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
        elif User.query.filter_by(username=username).first():
            flash("Username already taken.", "error")
        else:
            hashed = bcrypt.generate_password_hash(password).decode("utf-8")
            user   = User(username=username, email=email, password=hashed)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("dashboard.dashboard_page"))

    return render_template("auth.html", mode="signup")


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login_page"))