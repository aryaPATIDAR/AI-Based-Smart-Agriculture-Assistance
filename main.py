from flask import Flask, render_template, session, redirect
from backend.routes.auth import auth_bp
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'kisansmart_secret_key_2024'
app.register_blueprint(auth_bp)

# DB setup
import uuid
from backend.services.disease_service import predict_disease_sync
from backend.database.db import SessionLocal, engine
from backend.database.models import Base, DiseaseScan, Kisan, KisanFasal
from flask import request as flask_request
from werkzeug.utils import secure_filename

# DB tables create
Base.metadata.create_all(bind=engine)

# 🏠 Home Page
@app.route("/")
def home():
    data = {
        "crop": "Wheat",
        "status": "Healthy",
        "moisture": "70%",
        "temperature": "28°C"
    }
    reviews = []
    REVIEW_FILE = 'data/reviews.xlsx'
    if os.path.exists(REVIEW_FILE):
        df = pd.read_excel(REVIEW_FILE)
        approved = df[df['approved'] == 1]
        for _, row in approved.iterrows():
            reviews.append({
                'user_id'    : row['user_id'],
                'name'       : row['name'],
                'role'       : row['role'],
                'fasal'      : row['fasal'],
                'stars'      : int(row['stars']),
                'experience' : row['experience'],
                'date'       : row['date'],
                'photo'      : row['photo_base64'] if pd.notna(row['photo_base64']) else ''
            })
    return render_template("index.html", data=data,
                           logged_in=session.get('user_id') is not None,
                           reviews=reviews)

# 🚪 Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# 🌱 Disease Page
@app.route("/disease", methods=["GET", "POST"])
def disease():
    if not session.get('user_id'):
        return redirect("/")
    db = SessionLocal()
    kisan = db.query(Kisan).filter(Kisan.user_id == session['user_id']).first()
    if not kisan:
        kisan = Kisan(
            user_id=session['user_id'],
            naam="",
            phone=""
        )
        db.add(kisan)
        db.commit()
        db.refresh(kisan)
    fasalein = db.query(KisanFasal).filter(
        KisanFasal.kisan_id == kisan.id
    ).all() if kisan else []
    history = db.query(DiseaseScan).order_by(
        DiseaseScan.id.desc()
    ).limit(6).all()
    result = None
    uploaded_image = None
    selected_fasal = "Gehu"

    if flask_request.method == "POST":
        file = flask_request.files.get("file")
        selected_fasal = flask_request.form.get("fasal", "Gehu")
        if file:
            contents = file.read()
            ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
            filename = f"scan_{uuid.uuid4().hex[:8]}.{ext}"
            save_path = os.path.join("static", "uploads", filename)
            os.makedirs("static/uploads", exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(contents)
            uploaded_image = f"/static/uploads/{filename}"
            result = predict_disease_sync(contents)
            scan = DiseaseScan(
                kisan_id   = kisan.id if kisan else None,
                fasal      = selected_fasal,
                disease    = result["disease"],
                confidence = result["confidence"],
                solution   = result["solution"],
                precaution = result["precaution"],
                severity   = result.get("severity", "Low"),
                image_path = uploaded_image,
            )
            db.add(scan)
            db.commit()
            history = db.query(DiseaseScan).order_by(
                DiseaseScan.id.desc()
            ).limit(6).all()

    db.close()
    return render_template("disease.html",
                           kisan=kisan,
                           fasalein=fasalein,
                           history=history,
                           result=result,
                           uploaded_image=uploaded_image,
                           selected_fasal=selected_fasal)

# 🌦 Weather Page
@app.route("/weather")
def weather():
    return render_template("weather.html")




# 👨‍🌾 Farmer Page
@app.route("/farmer")
def farmer():
    if not session.get('user_id'):
        return redirect("/")  # Login nahi hai toh home bhejo
    db = SessionLocal()
    kisan = db.query(Kisan).filter(Kisan.user_id == session['user_id']).first()
    db.close()
    return render_template("farmer.html", kisan=kisan)

# 👨‍🌾 Farmer Page
@app.route("/farmer-profile", methods=["GET", "POST"])
def farmer_profile():
    if not session.get('user_id'):
        return redirect("/")
    db = SessionLocal()
    kisan = db.query(Kisan).filter(Kisan.user_id == session['user_id']).first()

    # Agar kisan nahi hai toh naya banao

    if not kisan:
        kisan = Kisan(
            user_id=session['user_id'],  # ← yeh add karo
            naam="", phone="", village="", district="", state=""
        )
        db.add(kisan)
        db.commit()
        db.refresh(kisan)

    if flask_request.method == "POST":
        kisan.naam        = flask_request.form.get("name")

        kisan.village     = flask_request.form.get("village")
        kisan.district    = flask_request.form.get("district")
        kisan.state       = flask_request.form.get("state")
        kisan.main_crop   = flask_request.form.get("main_crop")
        kisan.soil_type   = flask_request.form.get("soil_type")
        kisan.irrigation  = flask_request.form.get("irrigation")

        land = flask_request.form.get("land", 0)
        kisan.zameen_bigha = float(land) if land else 0.0

        exp = flask_request.form.get("experience", 0)
        kisan.experience = int(exp) if exp else 0

        # Photo save karo
        photo = flask_request.files.get("photo")
        if photo and photo.filename:
            upload_dir = os.path.join("static", "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            from werkzeug.utils import secure_filename
            filename = secure_filename(f"kisan_{kisan.id}_{photo.filename}")
            photo.save(os.path.join(upload_dir, filename))
            kisan.profile_photo = f"/static/uploads/{filename}"

        db.commit()

    db.refresh(kisan)
    response = render_template("farmer-profile.html", kisan=kisan)
    db.close()
    return response






# 🛡️ Admin Reviews
@app.route("/admin/reviews")
def admin_reviews():
    REVIEW_FILE = 'data/reviews.xlsx'
    if not os.path.exists(REVIEW_FILE):
        return "Koi review nahi hai abhi"
    df = pd.read_excel(REVIEW_FILE)
    rows = ""
    for i, row in df.iterrows():
        approved = "✅ Approved" if row['approved'] == 1 else f'<a href="/admin/approve/{i}">Approve Karo</a>'
        rows += f"""
        <tr>
            <td>{row['user_id']}</td><td>{row['name']}</td><td>{row['role']}</td>
            <td>{row['fasal']}</td><td>{'⭐' * int(row['stars'])}</td>
            <td>{str(row['experience'])[:80]}...</td><td>{row['date']}</td><td>{approved}</td>
        </tr>"""
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

# ✅ Approve Review
@app.route("/admin/approve/<int:idx>")
def approve_review(idx):
    REVIEW_FILE = 'data/reviews.xlsx'
    df = pd.read_excel(REVIEW_FILE)
    df.at[idx, 'approved'] = 1
    df.to_excel(REVIEW_FILE, index=False)
    return redirect('/admin/reviews')



#trader root

@app.route("/trader")
def trader():
    if not session.get('user_id'):
        return redirect("/")
    return render_template("trader.html")
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
