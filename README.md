# KisanSmart – AI-Based Smart Agriculture Assistance
## Integrated Crop Disease Detection Module

This project integrates a complete, production-ready AI-based **Crop Disease Detection** module into the **KisanSmart** platform. The existing technology stack (Flask, SQLite, SQLAlchemy, session-based authentication, Jinja2 frontend, and existing database models) has been strictly preserved.

---

## 1. Supported Crops and Disease Classes

The module supports exactly **six crops** with **28 scientifically verified disease and healthy conditions**:

### 1. Wheat (Gehu)
- **Leaf Rust** (*Puccinia triticina*): Orange-brown pustules on leaves. Solution: Propiconazole 25% EC @ 1 ml/L.
- **Loose Smut** (*Ustilago tritici*): Black powdery spore masses replacing wheat ears. Solution: Seed treatment with Carboxin + Thiram @ 2.5 g/kg.
- **Crown & Root Rot** (*Fusarium pseudograminearum*): Crown browning and whiteheads. Solution: Drenching with Carbendazim 50% WP @ 2 g/L.
- **Healthy Leaf**: Vigorous green foliage without lesions.

### 2. Rice (Dhan)
- **Bacterial Blight** (*Xanthomonas oryzae*): Water-soaked lesions turning straw-colored with wavy margins. Solution: Copper Oxychloride @ 2.5 g/L + Streptocycline @ 0.06 g/L.
- **Rice Blast** (*Magnaporthe oryzae*): Spindle-shaped lesions with brown margins and grey centers. Solution: Tricyclazole 75% WP @ 0.6 g/L.
- **Brown Spot** (*Bipolaris oryzae*): Oval brown spots with yellow halos. Solution: Mancozeb 75% WP @ 2 g/L.
- **Tungro Disease** (RTBV & RTSV): Severe stunting and yellow-orange leaves. Solution: Control green leafhopper vector with Imidacloprid @ 0.3 ml/L.

### 3. Tomato (Tamatar)
- **Bacterial Spot** (*Xanthomonas campestris*): Dark water-soaked spots with yellow halos. Solution: Copper Hydroxide @ 2 g/L + Mancozeb @ 2 g/L.
- **Early Blight** (*Alternaria solani*): Target-like concentric rings on older leaves. Solution: Chlorothalonil 75% WP @ 2 g/L.
- **Late Blight** (*Phytophthora infestans*): Rapid water-soaked dark lesions with white mold. Solution: Metalaxyl 8% + Mancozeb 64% WP @ 2.5 g/L.
- **Leaf Mold** (*Passalora fulva*): Olive-green velvety fungal growth on leaf undersides. Solution: Difenoconazole 25% EC @ 1 ml/L.
- **Mosaic Virus** (ToMV): Mottled light/dark green patches and leaf distortion. Solution: Rogue infected plants, sanitize tools, neem oil spray.
- **Septoria Leaf Spot** (*Septoria lycopersici*): Circular spots with brown margins and tiny black specks. Solution: Mancozeb 75% WP @ 2.5 g/L.
- **Target Spot** (*Corynespora cassiicola*): Concentric circular necrotic lesions. Solution: Pyraclostrobin 20% WG @ 1 g/L.
- **Yellow Leaf Curl Virus** (TYLCV): Upward curling, yellowing, severe stunting. Solution: Control whiteflies with Dinotefuran 20% SG @ 0.5 g/L.
- **Healthy Leaf**: Crisp, unblemished foliage and healthy blossoms.

### 4. Potato (Aalu)
- **Early Blight** (*Alternaria solani*): Brown angular spots with concentric target rings. Solution: Mancozeb 75% WP @ 2.5 g/L.
- **Late Blight** (*Phytophthora infestans*): Fast-spreading dark lesions with white downy mold. Solution: Cymoxanil 8% + Mancozeb 64% WP @ 2.5 g/L.
- **Healthy Leaf**: Lush dark-green canopy free of blight lesions.

### 5. Cotton (Kapas)
- **Alternaria Leaf Spot** (*Alternaria macrospora*): Circular brown spots with purple margins. Solution: Propiconazole 25% EC @ 1 ml/L.
- **Bacterial Blight / Angular Leaf Spot** (*Xanthomonas malvacearum*): Angular water-soaked lesions bounded by veinlets. Solution: Copper Oxychloride @ 2.5 g/L + Streptocycline @ 0.1 g/L.
- **Fusarium Wilt** (*Fusarium oxysporum*): Vascular browning, yellowing, upward wilting. Solution: Soil drench with Carbendazim @ 2 g/L.
- **Healthy Leaf**: Deep green foliage and healthy square formation.

### 6. Soybean (Soyabean)
- **Bacterial Blight** (*Pseudomonas syringae*): Angular translucent lesions turning brown with shredded edges. Solution: Copper Hydroxide @ 2 g/L + Streptocycline @ 0.05 g/L.
- **Frogeye Leaf Spot** (*Cercospora sojina*): Circular spots with reddish-purple borders and gray centers. Solution: Azoxystrobin + Difenoconazole @ 1 ml/L.
- **Asian Soybean Rust** (*Phakopsora pachyrhizi*): Tiny tan-to-reddish pustules on leaf undersides. Solution: Tebuconazole 25.9% EC @ 1.25 ml/L.
- **Healthy Leaf**: Uniform green trifoliate leaves without necrotic spots.

---

## 2. AI Model & Dataset Architecture

- **Base Architecture**: MobileNetV2 pre-trained on ImageNet with custom classification head (GlobalAveragePooling2D $\rightarrow$ BatchNorm $\rightarrow$ Dropout 0.35 $\rightarrow$ Dense 256 ReLU $\rightarrow$ Dropout 0.25 $\rightarrow$ Dense 28 Softmax).
- **Dataset Size**: 2,800 images across 28 balanced classes (100 images per class).
- **Split**: 70% Train (1,960 images), 15% Validation (420 images), 15% Independent Test (420 images).
- **Independent Test Performance**:
  - Overall Test Accuracy: **83.57%**
  - Macro Average Precision: **0.87 (87%)**
  - Macro Average Recall: **0.84 (84%)**
  - Macro Average F1-Score: **0.83 (83%)**
- **Model Files**:
  - `backend/models/crop_disease_model.keras` (~25.9 MB)
  - `backend/models/model.h5` (~25.7 MB)
  - `backend/models/class_indices.json` (class-to-index mapping)
  - `backend/models/disease_metadata.json` (symptoms, treatments, precautions, severity, survival rates)
  - `backend/models/test_metrics.json` (evaluation report and confusion matrix)

---

## 3. Workflow & Security

1. **Access Control**: Only authenticated farmers (`role == 'kisan'`) can access `/disease`. Unauthenticated visits redirect to `/`; traders redirect to `/trader`.
2. **Supported Formats**: JPG, JPEG, PNG, WEBP.
3. **Size Limit**: Enforced 10 MB maximum upload size on the backend.
4. **Pillow Verification**: The backend validates image integrity via `Image.open().verify()` before inference.
5. **Safe Persistence**: Images are saved to disk (`static/uploads/scan_*.ext`) and records are added to `DiseaseScan` only **after** successful AI prediction.
6. **Crop-Aware Conditioning**: When a crop is selected, softmax probabilities are conditioned over that crop's valid pathology classes, preventing cross-crop classification errors.

---

## 4. Setup and Execution

### Step 1: Install Dependencies
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Run Automated Acceptance Tests
```powershell
python tests/test_disease_module.py
```
This runs all 12 tests:
- Flask startup and blueprints.
- Home page loading.
- Farmer authentication.
- Unauthorized access blocking.
- Authenticated farmer access.
- 6-crop UI selection verification.
- Rejection of invalid / corrupted files.
- Rejection of files > 10 MB.
- Real inference verification on test images from all 6 crops.
- SQLite persistence in `DiseaseScan`.
- Scan history rendering.
- Continued operation of existing modules (`/weather`, `/farmer`, `/logout`).

### Step 3: Start the Flask Application
```powershell
python main.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 5. Directory Structure
```
KisanSmart/
├── backend/
│   ├── core/
│   │   ├── config.py
│   │   └── oauth.py
│   ├── database/
│   │   ├── db.py
│   │   └── models.py
│   ├── models/
│   │   ├── crop_disease_model.keras   # Trained AI model (.keras)
│   │   ├── model.h5                  # Trained AI model (.h5)
│   │   ├── class_indices.json         # 28-class label indices
│   │   ├── disease_metadata.json      # Symptoms, treatments, precautions
│   │   └── test_metrics.json          # Independent test evaluation results
│   ├── routes/
│   │   ├── admin.py
│   │   ├── auth.py
│   │   ├── disease.py                 # Disease detection route with validation & DB
│   │   ├── farmer.py
│   │   ├── home.py
│   │   ├── trader.py
│   │   └── weather.py
│   └── services/
│       ├── disease_service.py         # AI inference & crop conditioning service
│       ├── otp_service.py
│       ├── price_service.py
│       └── weather_service.py
├── scripts/
│   ├── download_dataset.py            # Dataset downloader & organizer
│   └── train_model.py                 # MobileNetV2 training & evaluation script
├── static/
│   ├── style.css
│   ├── images/
│   └── uploads/
├── templates/
│   ├── auth.html
│   ├── dashboard.html
│   ├── disease.html                   # Disease detection frontend UI
│   ├── farmer.html
│   ├── farmer-profile.html
│   ├── index.html
│   ├── trader.html
│   └── weather.html
├── tests/
│   └── test_disease_module.py         # 12-point acceptance test suite
├── main.py                            # Flask application entry point
├── models.py                          # Root SQLAlchemy models reference
└── requirements.txt                   # Verified dependency freeze
```
