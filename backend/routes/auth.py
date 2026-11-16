
from flask import (
    Blueprint, request, jsonify, session,
    redirect, url_for
)

import os
import base64
import uuid
from datetime import datetime

from backend.database.db import SessionLocal
from backend.database.models import Kisan, Review

from backend.services.otp_service import (
    send_otp, verify_otp, normalize_email, is_valid_email
)

from backend.core.config import UPLOAD_DIR
from backend.core.oauth import oauth


auth_bp = Blueprint('auth', __name__)

os.makedirs('data', exist_ok=True)


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def find_user(db, email):
    email = normalize_email(email)

    if not email:
        return None

    return db.query(Kisan).filter(
        Kisan.email == email
    ).first()


def make_id(db, role):
    """Unique user_id generate karta hai."""

    prefix = 'KS' if role == 'kisan' else 'VP'

    while True:
        uid = prefix + uuid.uuid4().hex[:6].upper()

        if not db.query(Kisan).filter(
            Kisan.user_id == uid
        ).first():
            return uid


def save_photo(photo_data):

    if not photo_data or len(photo_data) < 100:
        return ''

    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        ext = 'png' if 'png' in photo_data[:30] else 'jpg'

        filename = f"review_{uuid.uuid4().hex[:8]}.{ext}"

        img_data = (
            photo_data.split(',')[1]
            if ',' in photo_data
            else photo_data
        )

        with open(os.path.join(UPLOAD_DIR, filename), 'wb') as f:
            f.write(base64.b64decode(img_data))

        return f'/static/uploads/{filename}'

    except Exception:
        return ''


# --------------------------------------------------
# GOOGLE LOGIN
# --------------------------------------------------

@auth_bp.route('/google/login/<role>')
def google_login(role):

    if role not in ['kisan', 'vyapari']:
        return jsonify({
            'success': False,
            'message': 'Invalid user role'
        }), 400

    # Previous authentication state clear karo
    session.pop('google_verified', None)
    session.pop('google_registration_required', None)

    session['role'] = role
    session['google_role'] = role

    redirect_uri = url_for(
        'auth.google_callback',
        _external=True
    )

    # Debug: terminal mein exact Google callback URL dekhein.
    print("GOOGLE REDIRECT URI:", redirect_uri)

    try:
        return oauth.google.authorize_redirect(
            redirect_uri
        )

    except Exception as e:
        print("Google Login Error:", str(e))

        return jsonify({
            'success': False,
            'message': 'Google login start nahi ho paya'
        }), 500


# --------------------------------------------------
# GOOGLE CALLBACK
# --------------------------------------------------

@auth_bp.route('/google/callback')
def google_callback():

    db = SessionLocal()

    try:

        # Google se access token receive karo
        token = oauth.google.authorize_access_token()

        # Google user information
        user_info = token.get('userinfo')

        if not user_info:
            return "Google user information nahi mili", 400

        email = normalize_email(
            user_info.get('email', '')
        )

        email_verified = user_info.get('email_verified')

        # Verified email compulsory hai
        if not email or email_verified is not True:
            return "Google email verified nahi hai", 403

        role = session.get('google_role')

        if role not in ['kisan', 'vyapari']:
            return "Invalid user role", 400

        # Database mein existing user check
        user = find_user(db, email)

        if user:

            # Existing account ka role database se lo; selected UI role par depend mat karo.
            actual_role = user.role or role
            if actual_role not in ['kisan', 'vyapari']:
                return "Account ka role valid nahi hai. Support se contact karein.", 403

            session['user_id'] = user.user_id
            session['email'] = email
            session['role'] = actual_role

            session.pop('google_role', None)
            session.pop('google_verified', None)
            session.pop('google_registration_required', None)

            return redirect(url_for('auth.post_login'))

        # ------------------------------------------
        # NEW GOOGLE USER
        # ------------------------------------------

        google_name = user_info.get('name', '')

        session['email'] = email
        session['role'] = role

        session['google_verified'] = True
        session['google_registration_required'] = True
        session['google_name'] = google_name

        session.pop('user_id', None)

        return redirect('/')

    except Exception as e:

        print("Google OAuth Callback Error:", str(e))

        return "Google authentication failed", 400

    finally:
        db.close()


# --------------------------------------------------
# SEND OTP
# --------------------------------------------------

@auth_bp.route('/send-otp', methods=['POST'])
def send_otp_route():

    data = request.get_json() or {}

    email = normalize_email(data.get('email', ''))
    role = data.get('role', '')
    mode = data.get('mode', '')

    if not is_valid_email(email):
        return jsonify({
            'success': False,
            'message': 'Sahi email dalein'
        })

    if mode in ('register', 'login'):

        db = SessionLocal()

        try:
            user = find_user(db, email)

        finally:
            db.close()

        if mode == 'register' and user:
            return jsonify({
                'success': False,
                'message': 'Ye email already registered hai'
            })

        if mode == 'login' and not user:
            return jsonify({
                'success': False,
                'message': 'Email registered nahi — pehle register karein'
            })

        # Login ke liye role hamesha existing account se determine hoga.
        if mode == 'login':
            role = user.role or role
            if role not in ['kisan', 'vyapari']:
                return jsonify({
                    'success': False,
                    'message': 'Account ka role valid nahi hai'
                })

    if role not in ['kisan', 'vyapari']:
        return jsonify({'success': False, 'message': 'Invalid user role'})

    session['role'] = role
    session['email'] = email
    session['otp_verified'] = False

    session.pop('google_verified', None)

    ok, message = send_otp(email)

    return jsonify({
        'success': ok,
        'message': message
    })


# --------------------------------------------------
# VERIFY OTP
# --------------------------------------------------

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp_route():

    data = request.get_json() or {}

    email = session.get('email', '')
    entered = str(data.get('otp', ''))

    if not email:
        return jsonify({
            'success': False,
            'message': 'Pehle email dalkar OTP mangwayein'
        })

    ok, message = verify_otp(email, entered)

    if ok:
        session['otp_verified'] = True

    return jsonify({
        'success': ok,
        'message': message
    })


# --------------------------------------------------
# REGISTER
# --------------------------------------------------

@auth_bp.route('/register', methods=['POST'])
def register():

    # OTP ya Google verification required
    otp_verified = session.get('otp_verified', False)
    google_verified = session.get('google_verified', False)

    if not otp_verified and not google_verified:
        return jsonify({
            'success': False,
            'message': 'Pehle email verify karein'
        })

    data = request.get_json() or {}

    role = session.get('role', '')
    email = session.get('email', '')

    if role not in ['kisan', 'vyapari']:
        return jsonify({
            'success': False,
            'message': 'Invalid user role'
        })

    db = SessionLocal()

    try:

        existing = find_user(db, email)

        if existing:

            if existing.role and existing.role != role:
                return jsonify({
                    'success': False,
                    'message': 'Ye email doosre role me registered hai'
                })

            return jsonify({
                'success': False,
                'message': 'Email already registered hai'
            })

        user_id = make_id(db, role)

        # Google name se default name
        google_name = session.get('google_name', '')

        google_parts = google_name.split(' ', 1)

        first = data.get(
            'first_name',
            google_parts[0] if google_parts else ''
        )

        last = data.get(
            'last_name',
            google_parts[1] if len(google_parts) > 1 else ''
        )

        mobile = str(
            data.get('mobile', '') or ''
        ).strip() or None

        new_user = Kisan(
            user_id=user_id,
            first_name=first,
            last_name=last,
            naam=(first + ' ' + last).strip(),
            email=email,
            mobile=mobile,
            phone=mobile,
            gender=data.get('gender', ''),
            role=role,
            village=data.get('village', ''),
            district=data.get('city', ''),
            state=data.get('state', ''),
        )

        db.add(new_user)
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    session['user_id'] = user_id

    session['otp_verified'] = False
    session['google_verified'] = False
    session['google_registration_required'] = False

    session.pop('google_name', None)
    session.pop('google_role', None)

    return jsonify({
        'success': True,
        'user_id': user_id
    })


# --------------------------------------------------
# LOGIN CHECK - OTP
# --------------------------------------------------

@auth_bp.route('/login-check', methods=['POST'])
def login_check():

    if not session.get('otp_verified'):
        return jsonify({
            'success': False,
            'message': 'Pehle email OTP verify karein'
        })

    role = session.get('role', '')
    email = session.get('email', '')

    db = SessionLocal()

    try:

        user = find_user(db, email)

        if not user:
            return jsonify({
                'success': False,
                'message': 'Email registered nahi — pehle register karein'
            })

        actual_role = user.role or role
        if actual_role not in ['kisan', 'vyapari']:
            return jsonify({
                'success': False,
                'message': 'Account ka role valid nahi hai'
            })

        user_id = user.user_id

    finally:
        db.close()

    session['user_id'] = user_id
    session['role'] = actual_role
    session['email'] = email
    session['otp_verified'] = False

    return jsonify({
        'success': True,
        'user_id': user_id,
        'role': actual_role
    })


# --------------------------------------------------
# POST LOGIN ROLE DISPATCH
# --------------------------------------------------

@auth_bp.route('/post-login')
def post_login():
    """Load the account role from DB and send the user to the correct dashboard."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/')

    db = SessionLocal()
    try:
        user = db.query(Kisan).filter(Kisan.user_id == user_id).first()
        if not user or user.role not in ['kisan', 'vyapari']:
            session.clear()
            return redirect('/')

        session['role'] = user.role
        session['email'] = user.email or session.get('email', '')
        if user.role == 'kisan':
            return redirect('/farmer')
        return redirect('/trader')
    finally:
        db.close()


# --------------------------------------------------
# CHECK USER ID
# --------------------------------------------------

@auth_bp.route('/check-id', methods=['POST'])
def check_id():

    data = request.get_json() or {}

    user_id = str(
        data.get('user_id', '')
    ).strip()

    if not user_id or len(user_id) < 4:
        return jsonify({
            'success': False,
            'message': 'ID kam se kam 4 characters ki honi chahiye'
        })

    db = SessionLocal()

    try:

        taken = db.query(Kisan).filter(
            Kisan.user_id == user_id
        ).first()

    finally:
        db.close()

    if taken:
        return jsonify({
            'success': False,
            'message': 'Yeh ID pehle se li ja chuki hai, doosri try karein'
        })

    return jsonify({
        'success': True,
        'message': 'ID available hai!'
    })


# --------------------------------------------------
# SAVE USER ID
# --------------------------------------------------

@auth_bp.route('/save-id', methods=['POST'])
def save_id():

    if not session.get('user_id'):
        return jsonify({
            'success': False,
            'message': 'Pehle login karein'
        })

    data = request.get_json() or {}

    user_id = str(
        data.get('user_id', '')
    ).strip()

    email = session.get('email', '')

    if len(user_id) < 4:
        return jsonify({
            'success': False,
            'message': 'ID kam se kam 4 characters ki honi chahiye'
        })

    db = SessionLocal()

    try:

        user = find_user(db, email)

        if not user:
            return jsonify({
                'success': False,
                'message': 'User nahi mila'
            })

        taken = db.query(Kisan).filter(
            Kisan.user_id == user_id,
            Kisan.email != email
        ).first()

        if taken:
            return jsonify({
                'success': False,
                'message': 'Yeh ID pehle se li ja chuki hai'
            })

        user.user_id = user_id

        db.commit()

    finally:
        db.close()

    session['user_id'] = user_id

    return jsonify({
        'success': True,
        'user_id': user_id
    })


# --------------------------------------------------
# SUBMIT REVIEW
# --------------------------------------------------

@auth_bp.route('/submit-review', methods=['POST'])
def submit_review():

    data = request.get_json() or {}

    user_id = session.get('user_id', '')
    role = session.get('role', '')
    email = session.get('email', '')

    if not user_id:
        return jsonify({
            'success': False,
            'message': 'Pehle login karein'
        })

    db = SessionLocal()

    try:

        user = find_user(db, email)

        name = (
            user.naam
            if user and user.naam
            else user_id
        )

        location = (
            user.state
            if user and user.state
            else ''
        )

        db.add(Review(
            user_id=user_id,
            role=role,
            name=name,
            location=location,
            fasal=data.get('fasal', ''),
            stars=int(data.get('stars') or 5),
            experience=data.get('experience', ''),
            photo_path=save_photo(data.get('photo', '')),
            approved=False,
            date=datetime.now().strftime('%d-%m-%Y'),
        ))

        db.commit()

    finally:
        db.close()

    return jsonify({
        'success': True,
        'message': 'Review submit ho gaya!'
    })
