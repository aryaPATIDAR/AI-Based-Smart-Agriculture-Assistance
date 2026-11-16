import os
import uuid
import logging
from flask import Blueprint, render_template, request, session, redirect, flash
from werkzeug.utils import secure_filename
from backend.database.db import SessionLocal
from backend.database.models import Kisan, KisanFasal, DiseaseScan
from backend.services.disease_service import predict_disease_sync, normalize_crop_name

logger = logging.getLogger(__name__)

disease_bp = Blueprint("disease", __name__)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit

# Valid crops supported by the module
VALID_CROPS = ["Gehu", "Dhan", "Tomato", "Aalu", "Kapas", "Soyabean"]


@disease_bp.route("/disease", methods=["GET", "POST"])
def disease():
    # 1. Farmer Authentication Check
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/")

    role = session.get("role", "kisan")
    if role != "kisan":
        return redirect("/trader" if role == "vyapari" else "/")

    db = SessionLocal()
    try:
        kisan = db.query(Kisan).filter(Kisan.user_id == user_id).first()
        if not kisan:
            kisan = Kisan(user_id=user_id, naam="Kisan", phone="", role="kisan")
            db.add(kisan)
            db.commit()
            db.refresh(kisan)

        fasalein = db.query(KisanFasal).filter(KisanFasal.kisan_id == kisan.id).all()
        result = None
        uploaded_image = None
        selected_fasal = "Gehu"
        error_msg = None

        if request.method == "POST":
            selected_fasal = request.form.get("fasal", "Gehu").strip()
            if selected_fasal not in VALID_CROPS:
                selected_fasal = "Gehu"

            file = request.files.get("file")
            if not file or not file.filename:
                error_msg = "Kripya patti ki ek photo chunein."
            else:
                filename_clean = secure_filename(file.filename)
                ext = filename_clean.rsplit(".", 1)[-1].lower() if "." in filename_clean else ""

                if ext not in ALLOWED_EXTENSIONS:
                    error_msg = f"Sirf JPG, JPEG, PNG, aur WEBP formats allowed hain. (Aapki file: .{ext})"
                else:
                    contents = file.read()
                    
                    # Enforce 10MB limit
                    if len(contents) > MAX_FILE_SIZE:
                        error_msg = "Photo 10MB se badi hai. Kripya 10MB se chhoti photo upload karein."
                    elif len(contents) < 10:
                        error_msg = "Khali ya corrupted photo file mili."
                    else:
                        try:
                            # Run real AI inference BEFORE saving file to disk
                            result = predict_disease_sync(contents, crop_hint=selected_fasal)

                            # Save image only AFTER successful prediction
                            upload_dir = os.path.join("static", "uploads")
                            os.makedirs(upload_dir, exist_ok=True)
                            safe_name = f"scan_{uuid.uuid4().hex[:12]}.{ext}"
                            disk_path = os.path.join(upload_dir, safe_name)
                            with open(disk_path, "wb") as f:
                                f.write(contents)
                            uploaded_image = f"/static/uploads/{safe_name}"

                            # Persist prediction in existing SQLite database
                            scan_record = DiseaseScan(
                                kisan_id=kisan.id,
                                fasal=selected_fasal,
                                disease=result["disease"],
                                confidence=result["confidence"],
                                severity=result.get("severity", "Low"),
                                solution=result["solution"],
                                precaution=result["precaution"],
                                image_path=uploaded_image,
                            )
                            db.add(scan_record)
                            db.commit()
                            db.refresh(scan_record)

                        except ValueError as ve:
                            logger.warning("Image validation failed: %s", ve)
                            error_msg = str(ve)
                        except RuntimeError as re:
                            logger.error("AI Model error: %s", re)
                            error_msg = "AI Model uplabdh nahi hai ya load nahi ho paya. Kripya system administrator se sampark karein."
                        except Exception as e:
                            logger.exception("Unexpected error during disease scan: %s", e)
                            error_msg = "Scan karte samay takneeki kharabi aayi. Kripya dobara prayas karein."

        # Fetch authenticated farmer's scan history
        history = (
            db.query(DiseaseScan)
            .filter(DiseaseScan.kisan_id == kisan.id)
            .order_by(DiseaseScan.id.desc())
            .limit(9)
            .all()
        )

        return render_template(
            "disease.html",
            kisan=kisan,
            fasalein=fasalein,
            history=history,
            result=result,
            uploaded_image=uploaded_image,
            selected_fasal=selected_fasal,
            error_msg=error_msg,
            valid_crops=VALID_CROPS
        )

    finally:
        db.close()
