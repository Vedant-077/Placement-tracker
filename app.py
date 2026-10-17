import os
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, send_from_directory, abort)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
import storage

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "login"

STATUSES = ["Applied", "Test Cleared", "Interview", "Offered", "Rejected"]
ALLOWED = {"pdf", "doc", "docx"}


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    company = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(30), default="Applied")
    resume_key = db.Column(db.String(255))


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)
    with app.app_context():
        db.create_all()

    @app.route("/health")
    def health():
        return {"status": "ok"}

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            email = request.form["email"].strip().lower()
            password = request.form["password"]
            if not email or len(password) < 6:
                flash("Enter an email and a password of at least 6 characters.")
            elif User.query.filter_by(email=email).first():
                flash("This email is already registered.")
            else:
                db.session.add(User(email=email, password_hash=generate_password_hash(password)))
                db.session.commit()
                flash("Account created! Please log in.")
                return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            user = User.query.filter_by(email=request.form["email"].strip().lower()).first()
            if user and check_password_hash(user.password_hash, request.form["password"]):
                login_user(user)
                return redirect(url_for("dashboard"))
            flash("Wrong email or password.")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def dashboard():
        apps = Application.query.filter_by(user_id=current_user.id).all()
        for a in apps:
            a.link = storage.get_download_url(a.resume_key, url_for("local_file", key=a.resume_key)) if a.resume_key else None
        return render_template("dashboard.html", apps=apps, statuses=STATUSES)

    @app.route("/add", methods=["POST"])
    @login_required
    def add():
        item = Application(user_id=current_user.id,
                           company=request.form["company"].strip(),
                           role=request.form["role"].strip(),
                           status=request.form.get("status", "Applied"))
        f = request.files.get("resume")
        if f and f.filename:
            if f.filename.rsplit(".", 1)[-1].lower() not in ALLOWED:
                flash("Only PDF/DOC/DOCX resumes are allowed.")
                return redirect(url_for("dashboard"))
            item.resume_key = storage.save_file(f)
        db.session.add(item)
        db.session.commit()
        return redirect(url_for("dashboard"))

    @app.route("/status/<int:app_id>", methods=["POST"])
    @login_required
    def update_status(app_id):
        item = db.session.get(Application, app_id)
        if not item or item.user_id != current_user.id:
            abort(404)
        if request.form["status"] in STATUSES:
            item.status = request.form["status"]
            db.session.commit()
        return redirect(url_for("dashboard"))

    @app.route("/delete/<int:app_id>", methods=["POST"])
    @login_required
    def delete(app_id):
        item = db.session.get(Application, app_id)
        if not item or item.user_id != current_user.id:
            abort(404)
        db.session.delete(item)
        db.session.commit()
        return redirect(url_for("dashboard"))

    @app.route("/files/<key>")
    @login_required
    def local_file(key):  # used only when S3 is not configured
        owns = Application.query.filter_by(user_id=current_user.id, resume_key=key).first()
        if not owns:
            abort(404)
        return send_from_directory(storage.LOCAL_DIR, key, as_attachment=True)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
