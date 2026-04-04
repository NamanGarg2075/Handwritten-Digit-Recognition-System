# app.py
import os
from flask import Flask, redirect, render_template, url_for
from flask_login import current_user, login_required
from config import Config
from extensions import db, login, bcrypt
from models import User, Prediction   # noqa: F401 — needed for db.create_all()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)
    login.init_app(app)
    bcrypt.init_app(app)

    # Register blueprints
    from routes.auth      import auth
    from routes.predict   import predict_bp, load_model
    from routes.dashboard import dashboard

    app.register_blueprint(auth)
    app.register_blueprint(predict_bp)
    app.register_blueprint(dashboard)

    # Home → redirect based on auth state
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.dashboard_page"))
        return redirect(url_for("auth.login_page"))
    
    # Tool page (for drawing digits) - requires login
    @app.route("/tool")
    @login_required
    def tool():
        return render_template("index.html")

    # Create DB tables + load model
    with app.app_context():
        db.create_all()
        load_model()
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    return app



if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)