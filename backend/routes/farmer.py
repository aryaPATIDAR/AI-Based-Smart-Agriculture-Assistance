import os
import uuid
from flask import Blueprint, render_template, session, redirect, request, flash
from werkzeug.utils import secure_filename
from backend.database.db import SessionLocal
from backend.database.models import Kisan
from backend.core.config import UPLOAD_DIR

farmer_bp = Blueprint("farmer", __name__)


def _farmer_required():
    if not session.get("user_id"):
        return redirect("/")
    if session.get("role") != "kisan":
        return redirect("/trader" if session.get("role") == "vyapari" else "/")
    return None


def _get_farmer(db):
    return db.query(Kisan).filter(
        Kisan.user_id == session["user_id"],
        Kisan.role == "kisan"
    ).first()


@farmer_bp.route("/farmer")
def farmer():
    denied = _farmer_required()
    if denied:
        return denied

    db = SessionLocal()
    try:
        kisan = _get_farmer(db)
        if kisan is None:
            session.clear()
            return redirect("/")
        return render_template("farmer.html", kisan=kisan)
    finally:
        db.close()


@farmer_bp.route("/farmer-profile", methods=["GET", "POST"])
def farmer_profile():
    denied = _farmer_required()
    if denied:
        return denied

    db = SessionLocal()
    try:
        kisan = _get_farmer(db)
        if kisan is None:
            session.clear()
            return redirect("/")

        if request.method == "POST":
            kisan.naam = (request.form.get("name") or "").strip() or kisan.naam
            # Registered mobile number is intentionally not overwritten from this form.
            kisan.village = (request.form.get("village") or "").strip()
            kisan.district = (request.form.get("district") or "").strip()
            kisan.state = (request.form.get("state") or "").strip()
            kisan.main_crop = (request.form.get("main_crop") or "").strip()
            kisan.soil_type = request.form.get("soil_type") or None
            kisan.irrigation = request.form.get("irrigation") or None

            land_raw = (request.form.get("land") or "").strip()
            exp_raw = (request.form.get("experience") or "").strip()
            try:
                land = float(land_raw) if land_raw else None
                experience = int(exp_raw) if exp_raw else None
                if land is not None and land < 0:
                    raise ValueError
                if experience is not None and experience < 0:
                    raise ValueError
            except ValueError:
                flash("Land aur experience mein valid positive number dalein.", "error")
                return render_template("farmer-profile.html", kisan=kisan)

            kisan.zameen_bigha = land
            kisan.experience = experience

            photo = request.files.get("photo")
            if photo and photo.filename:
                os.makedirs(UPLOAD_DIR, exist_ok=True)
                safe_name = secure_filename(photo.filename)
                ext = os.path.splitext(safe_name)[1].lower()
                if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
                    flash("Profile photo JPG, PNG ya WEBP format mein upload karein.", "error")
                    return render_template("farmer-profile.html", kisan=kisan)
                filename = f"kisan_{kisan.id}_{uuid.uuid4().hex[:10]}{ext}"
                photo.save(os.path.join(UPLOAD_DIR, filename))
                kisan.profile_photo = f"/static/uploads/{filename}"

            db.commit()
            flash("Profile successfully update ho gayi.", "success")

        return render_template("farmer-profile.html", kisan=kisan)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
