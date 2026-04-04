# routes/dashboard.py
import os
from flask import Blueprint, render_template, jsonify, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Prediction

dashboard = Blueprint("dashboard", __name__)


@dashboard.route("/dashboard")
@login_required
def dashboard_page():
    predictions = (
        Prediction.query
        .filter_by(user_id=current_user.id)
        .order_by(Prediction.created_at.desc())
        .all()
    )
    return render_template("dashboard.html", predictions=predictions)


@dashboard.route("/api/predictions")
@login_required
def get_predictions():
    preds = (
        Prediction.query
        .filter_by(user_id=current_user.id)
        .order_by(Prediction.created_at.desc())
        .all()
    )
    return jsonify([p.to_dict() for p in preds])


@dashboard.route("/api/predictions/<int:pred_id>", methods=["DELETE"])
@login_required
def delete_prediction(pred_id):
    pred = Prediction.query.filter_by(id=pred_id, user_id=current_user.id).first_or_404()

    # Delete snapshot file if exists
    if pred.snapshot:
        fpath = os.path.join(current_app.config["UPLOAD_FOLDER"], pred.snapshot)
        if os.path.exists(fpath):
            os.remove(fpath)

    db.session.delete(pred)
    db.session.commit()
    return jsonify({"success": True})