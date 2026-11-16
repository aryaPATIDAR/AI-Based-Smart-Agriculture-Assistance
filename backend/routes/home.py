from flask import Blueprint, render_template, session, redirect
from backend.database.db import SessionLocal
from backend.database.models import Review

home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def home():
    data = {
        "crop": "Wheat",
        "status": "Healthy",
        "moisture": "70%",
        "temperature": "28°C",
    }

    db = SessionLocal()
    try:
        rows = db.query(Review).filter(Review.approved == True).order_by(Review.id.desc()).all()
        reviews = [{
            "user_id": r.user_id,
            "name": r.name,
            "role": r.role,
            "fasal": r.fasal,
            "stars": r.stars or 5,
            "experience": r.experience,
            "date": r.date,
            "photo": r.photo_path or "",
        } for r in rows]
    finally:
        db.close()

    return render_template(
        "index.html",
        data=data,
        logged_in=session.get("user_id") is not None,
        reviews=reviews,
    )


@home_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")