# models.py
from extensions import db, login
from flask_login import UserMixin
from datetime import datetime

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(80),  unique=True, nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False)   # bcrypt hash
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    predictions = db.relationship("Prediction", backref="user", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"


class Prediction(db.Model):
    __tablename__ = "predictions"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    digit        = db.Column(db.Integer, nullable=False)
    confidence   = db.Column(db.Float,   nullable=False)
    top3         = db.Column(db.JSON,    nullable=True)   # stores top-3 list
    snapshot     = db.Column(db.String(255), nullable=True)  # filename of saved canvas image
    source       = db.Column(db.String(20), default="canvas")  # "canvas" or "upload"
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":         self.id,
            "digit":      self.digit,
            "confidence": self.confidence,
            "top3":       self.top3,
            "snapshot":   self.snapshot,
            "source":     self.source,
            "created_at": self.created_at.strftime("%d %b %Y, %H:%M"),
        }