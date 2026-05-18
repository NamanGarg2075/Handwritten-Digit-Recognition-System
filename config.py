# config.py
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "synapse-secret-key-change-in-production")

    # ── MySQL via SQLAlchemy ──────────────────────────────
    # Format: mysql+pymysql://username:password@host/database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://naman:naman1%40DMR@erp.dmrbuilders.in/synapse_db"
        #                    ^^^^ your MySQL password here (blank if none)
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Prediction snapshot storage ───────────────────────
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "snapshots")