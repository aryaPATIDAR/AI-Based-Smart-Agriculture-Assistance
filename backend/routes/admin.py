from flask import Blueprint, redirect
from markupsafe import escape
from backend.database.db import SessionLocal
from backend.database.models import Review

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin/reviews")
def admin_reviews():
    db = SessionLocal()
    try:
        reviews = db.query(Review).order_by(Review.id.desc()).all()
        if not reviews:
            return "Koi review nahi hai abhi"
        rows = ""
        for r in reviews:
            action = (
                "✅ Approved"
                if r.approved
                else f'<a href="/admin/approve/{r.id}">Approve Karo</a>'
            )
            rows += f"""
            <tr>
                <td>{escape(r.user_id)}</td><td>{escape(r.name)}</td><td>{escape(r.role)}</td>
                <td>{escape(r.fasal)}</td><td>{'⭐' * (r.stars or 0)}</td>
                <td>{escape(str(r.experience or '')[:80])}...</td><td>{escape(r.date)}</td><td>{action}</td>
            </tr>"""
    finally:
        db.close()

    return f"""<html><head><style>
    body{{font-family:sans-serif;padding:30px}}
    table{{border-collapse:collapse;width:100%}}
    th,td{{border:1px solid #ddd;padding:10px;font-size:13px}}
    th{{background:#1d9e75;color:white}}
    a{{color:#1d9e75;font-weight:600}}
    </style></head><body>
    <h2>🌱 KisanSmart — Review Panel</h2>
    <table><tr>
        <th>ID</th><th>Naam</th><th>Role</th><th>Fasal</th>
        <th>Stars</th><th>Experience</th><th>Date</th><th>Action</th>
    </tr>{rows}</table></body></html>"""


@admin_bp.route("/admin/approve/<int:review_id>")
def approve_review(review_id):
    db = SessionLocal()
    try:
        r = db.query(Review).filter(Review.id == review_id).first()
        if r:
            r.approved = True
            db.commit()
    finally:
        db.close()
    return redirect("/admin/reviews")