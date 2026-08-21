from flask import Blueprint, request, jsonify, session
import pandas as pd
import os
import base64
import uuid
from datetime import datetime
from backend.services.otp_service import generate_otp, verify_otp

auth_bp = Blueprint('auth', __name__)

DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

KISAN_FILE   = os.path.join(DATA_DIR, 'kisan_users.xlsx')
VYAPARI_FILE = os.path.join(DATA_DIR, 'vyapari_users.xlsx')

COLS = ['user_id','first_name','last_name','mobile',
        'city','village','state','gender','role']

def get_df(role):
    file = KISAN_FILE if role == 'kisan' else VYAPARI_FILE
    if os.path.exists(file):
        return pd.read_excel(file), file
    return pd.DataFrame(columns=COLS), file

def save_df(df, file):
    df.to_excel(file, index=False)

def make_id(mobile, role):
    prefix = 'KS' if role == 'kisan' else 'VP'
    return prefix + str(mobile)[-6:]

def save_photo(photo_data):
    if not photo_data or len(photo_data) < 100:
        return ''
    try:
        UPLOAD_DIR = os.path.join('static', 'uploads')
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = 'png' if 'png' in photo_data[:30] else 'jpg'
        filename = f"review_{uuid.uuid4().hex[:8]}.{ext}"
        img_data = photo_data.split(',')[1] if ',' in photo_data else photo_data
        with open(os.path.join(UPLOAD_DIR, filename), 'wb') as f:
            f.write(base64.b64decode(img_data))
        return f'/static/uploads/{filename}'
    except:
        return ''

@auth_bp.route('/send-otp', methods=['POST'])
def send_otp():
    data   = request.get_json()
    mobile = str(data.get('mobile', ''))
    role   = data.get('role', '')
    if len(mobile) != 10 or not mobile.isdigit():
        return jsonify({'success': False, 'message': 'Sahi 10-digit mobile dalein'})
    session['role']   = role
    session['mobile'] = mobile
    otp = generate_otp(mobile)
    return jsonify({'success': True, 'message': 'OTP bheja gaya', 'dev_otp': otp})

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp_route():
    data    = request.get_json()
    mobile  = session.get('mobile', '')
    entered = str(data.get('otp', ''))
    if verify_otp(mobile, entered):
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Galat OTP, dobara try karein'})

@auth_bp.route('/register', methods=['POST'])
def register():
    data   = request.get_json()
    role   = session.get('role', '')
    mobile = session.get('mobile', '')
    df, file = get_df(role)
    if mobile in df['mobile'].astype(str).values:
        return jsonify({'success': False, 'message': 'Mobile already registered hai'})
    user_id = make_id(mobile, role)
    new_row = {
        'user_id'    : user_id,
        'first_name' : data.get('first_name', ''),
        'last_name'  : data.get('last_name', ''),
        'mobile'     : mobile,
        'phone'      : mobile,
        'city'       : data.get('city', ''),
        'village'    : data.get('village', ''),
        'state'      : data.get('state', ''),
        'gender'     : data.get('gender', ''),
        'role'       : role
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_df(df, file)

    # DB me bhi save karo (sirf kisan role ke liye)
    if role == 'kisan':
        from backend.database.db import SessionLocal
        from backend.database.models import Kisan as KisanDB
        db = SessionLocal()
        kisan = db.query(KisanDB).filter(KisanDB.phone == mobile).first()
        if not kisan:
            kisan = KisanDB(
                user_id=user_id,
                naam=(data.get('first_name','') + ' ' + data.get('last_name','')).strip(),
                phone=mobile,
                village=data.get('village',''),
                district=data.get('city',''),
                state=data.get('state',''),
            )
            db.add(kisan)
        else:
            kisan.user_id  = user_id
            kisan.naam     = (data.get('first_name','') + ' ' + data.get('last_name','')).strip()
            kisan.village  = data.get('village','')
            kisan.district = data.get('city','')
            kisan.state    = data.get('state','')
        db.commit()
        db.close()

    session['user_id'] = user_id
    return jsonify({'success': True, 'user_id': user_id})

@auth_bp.route('/login-check', methods=['POST'])
def login_check():
    role   = session.get('role', '')
    mobile = session.get('mobile', '')
    df, _  = get_df(role)
    user   = df[df['mobile'].astype(str) == mobile]
    if user.empty:
        return jsonify({'success': False, 'message': 'Mobile registered nahi — pehle register karein'})
    user_id = user.iloc[0]['user_id']

    session['user_id'] = user_id
    return jsonify({'success': True, 'user_id': user_id})

@auth_bp.route('/check-id', methods=['POST'])
def check_id():
    data    = request.get_json()
    user_id = str(data.get('user_id', '')).strip()

    if not user_id or len(user_id) < 4:
        return jsonify({'success': False, 'message': 'ID kam se kam 4 characters ki honi chahiye'})

    for r in ['kisan', 'vyapari']:
        df, _ = get_df(r)
        if user_id in df['user_id'].astype(str).values:
            return jsonify({'success': False, 'message': 'Yeh ID pehle se li ja chuki hai, doosri try karein'})

    return jsonify({'success': True, 'message': 'ID available hai!'})

@auth_bp.route('/save-id', methods=['POST'])
def save_id():
    data    = request.get_json()
    user_id = str(data.get('user_id', '')).strip()
    role    = session.get('role', '')
    mobile  = session.get('mobile', '')

    df, file = get_df(role)
    df.loc[df['mobile'].astype(str) == mobile, 'user_id'] = user_id
    save_df(df, file)

    from backend.database.db import SessionLocal
    from backend.database.models import Kisan as KisanDB
    db = SessionLocal()
    kisan = db.query(KisanDB).filter(KisanDB.phone == mobile).first()
    if kisan:
        kisan.user_id = user_id
        db.commit()
    db.close()
    session['user_id'] = user_id
    return jsonify({'success': True, 'user_id': user_id})

@auth_bp.route('/submit-review', methods=['POST'])
def submit_review():
    data    = request.get_json()
    user_id = session.get('user_id', '')
    role    = session.get('role', '')
    mobile  = session.get('mobile', '')

    if not user_id:
        return jsonify({'success': False, 'message': 'Pehle login karein'})

    df_user, _ = get_df(role)
    user_row   = df_user[df_user['mobile'].astype(str) == str(mobile)]

    if not user_row.empty:
        fname    = str(user_row.iloc[0]['first_name']) if pd.notna(user_row.iloc[0]['first_name']) else ''
        lname    = str(user_row.iloc[0]['last_name'])  if pd.notna(user_row.iloc[0]['last_name'])  else ''
        name     = (fname + ' ' + lname).strip() or user_id
        location = str(user_row.iloc[0]['state']) if pd.notna(user_row.iloc[0]['state']) else ''
    else:
        name     = user_id
        location = ''

    REVIEW_FILE = os.path.join(DATA_DIR, 'reviews.xlsx')
    REVIEW_COLS = ['user_id','role','name','location','fasal',
                   'stars','experience','photo_base64','approved','date']

    if os.path.exists(REVIEW_FILE):
        rdf = pd.read_excel(REVIEW_FILE)
    else:
        rdf = pd.DataFrame(columns=REVIEW_COLS)

    new_review = {
        'user_id'      : user_id,
        'role'         : role,
        'name'         : name,
        'location'     : location,
        'fasal'        : data.get('fasal', ''),
        'stars'        : data.get('stars', 5),
        'experience'   : data.get('experience', ''),
        'photo_base64' : save_photo(data.get('photo', '')),
        'approved'     : 0,
        'date'         : datetime.now().strftime('%d-%m-%Y')
    }

    rdf = pd.concat([rdf, pd.DataFrame([new_review])], ignore_index=True)
    rdf.to_excel(REVIEW_FILE, index=False)

    return jsonify({'success': True, 'message': 'Review submit ho gaya!'})