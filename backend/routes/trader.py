from flask import Blueprint, render_template, session, redirect, request, flash
from backend.database.db import SessionLocal
from backend.database.models import Kisan

trader_bp = Blueprint("trader", __name__)


def _trader_required():
    if not session.get("user_id"):
        return redirect("/")
    if session.get("role") != "vyapari":
        return redirect("/farmer" if session.get("role") == "kisan" else "/")
    return None


@trader_bp.route("/trader")
def trader():
    denied = _trader_required()
    if denied:
        return denied

    db = SessionLocal()
    try:
        trader_user = db.query(Kisan).filter(
            Kisan.user_id == session["user_id"],
            Kisan.role == "vyapari"
        ).first()
        if trader_user is None:
            session.clear()
            return redirect("/")
        return render_template("trader.html", trader=trader_user)
    finally:
        db.close()


@trader_bp.route("/trader-profile", methods=["GET", "POST"])
def trader_profile():
    denied = _trader_required()
    if denied:
        return denied

    db = SessionLocal()
    try:
        trader_user = db.query(Kisan).filter(
            Kisan.user_id == session["user_id"],
            Kisan.role == "vyapari"
        ).first()
        if trader_user is None:
            session.clear()
            return redirect("/")

        if request.method == "POST":
            trader_user.naam = (request.form.get("name") or "").strip() or trader_user.naam
            # Mobile/email are verified registration identifiers; never clear them
            # because readonly fields are not submitted by the browser.
            trader_user.village = (request.form.get("village") or "").strip()
            trader_user.district = (request.form.get("district") or "").strip()
            trader_user.state = (request.form.get("state") or "").strip()
            trader_user.location = (request.form.get("location") or "").strip()
            db.commit()
            flash("Profile successfully update ho gayi.", "success")

        return render_template("trader-profile.html", trader=trader_user)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
