🌾 KisanSmart
AI-Based Smart Agriculture Assistance

An AI-assisted web platform for crop disease identification and digital farming support.

Python Flask TensorFlow Keras Show Image

</div>
Table of Contents
Overview
Key Features
Screenshots
Tech Stack
Architecture
Project Structure
How Disease Detection Works
Getting Started
Model and Evaluation
Testing
Challenges and Learnings
Future Scope
Disclaimer
Author
Overview

Crop disease symptoms are hard to spot early, and farmers don't always have quick access to reliable guidance. KisanSmart brings crop disease prediction and farmer-focused digital services into a single Flask web application.

A user uploads a crop image, a trained TensorFlow/Keras model classifies it, and the app shows the predicted disease along with related information. The app also has separate farmer and trader interfaces, an authentication flow with OTP service, and a weather module.

Key Features
AI crop disease detection: upload a crop image and get a prediction from the Keras model
Disease metadata: model output classes are mapped to labels and disease information
Farmer interface: farmer pages and profile
Trader interface: trader pages and profile
Authentication: login flow with OTP-related service
Weather module: weather information inside the app
Database: SQLAlchemy models with SQLite for local development
Modular backend: routes, services, core config and database kept in separate modules
Screenshots
Home Page	Farmer Dashboard
Home	Farmer Dashboard
Disease Detection	Prediction Result
Disease Detection	Prediction Result
Weather	Trader Dashboard
Weather	Trader Dashboard
Tech Stack
Layer	Technologies
Language	Python
Backend	Flask
Frontend	HTML, CSS, JavaScript, Jinja templates
Database	SQLite, SQLAlchemy
Machine Learning	TensorFlow, Keras (.keras model format)
Tools	Git, GitHub, PyCharm
Architecture
            User / Browser
                  │ HTTP
                  ▼
          Flask App (main.py)
                  │
     ┌────────────┼─────────────┐
     ▼            ▼             ▼
  Routes     Service Layer    Jinja
 (Auth /    (Disease / OTP)  Templates
 Farmer /          │
 Trader)           ▼
     │      TensorFlow / Keras Model
     ▼
 SQLAlchemy + SQLite

The browser sends a request to Flask, the matching route calls the service layer, database or ML model, and the result is rendered through the web interface.

Project Structure
AI-Based-Smart-Agriculture-Assistance/
├── backend/
│   ├── core/          # Configuration and core utilities
│   ├── database/      # DB connection and ORM models
│   ├── models/        # Trained model and class metadata
│   ├── routes/        # Flask route blueprints
│   └── services/      # Disease prediction, OTP logic
├── scripts/
│   ├── download_dataset.py
│   └── train_model.py
├── static/images/
├── templates/         # Jinja HTML templates
├── tests/
├── main.py            # Entry point
├── models.py
└── requirements.txt
How Disease Detection Works
User uploads a crop image on the disease detection page
Backend receives the image and preprocesses it
The Keras model classifies the image
The predicted index is mapped to a label using class_indices.json
Disease details are fetched from disease_metadata.json
The result is shown in the app
File	Purpose
backend/models/crop_disease_model.keras	Trained model
backend/models/class_indices.json	Index to class label mapping
backend/models/disease_metadata.json	Disease information
backend/models/test_metrics.json	Metrics from the training workflow
Getting Started

Prerequisites: Python 3.x, Git, and enough disk space/RAM for TensorFlow.

bash
# 1. Clone
git clone https://github.com/aryaPATIDAR/AI-Based-Smart-Agriculture-Assistance.git
cd AI-Based-Smart-Agriculture-Assistance

# 2. Virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate       # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python main.py

Open the URL printed in the terminal (usually http://127.0.0.1:5000).

Environment variables: create a .env file in the project root:

env
SECRET_KEY=replace_with_a_long_random_secret
# Add API keys for the weather / OTP services here

Never commit .env, API keys or the local database. Don't run Flask in debug mode in production.

Model and Evaluation
<!-- TODO: fill these from test_metrics.json and train_model.py, then delete this comment -->
Item	Details
Dataset	add dataset name and source
Number of classes	add number
Model architecture	add (e.g. custom CNN / MobileNetV2)
Test accuracy	add value from test_metrics.json

These metrics come from the project's own test split and should not be treated as verified real-world performance. Photos taken in real fields can differ a lot from dataset images.

Testing
bash
pytest

Tests are in the tests/ folder.

Challenges and Learnings
<!-- TODO: replace with your own real problems. Format: Problem -> Cause -> Fix -->
Model loading across TensorFlow versions: the saved Keras model must match the installed TensorFlow/Keras version.
Preprocessing mismatch: image size and scaling at prediction time must match what was used in training.
Label order: class_indices.json must stay in the same order as the model output.
Secrets: API keys are kept in .env and excluded from Git.
Future Scope
Evaluate the model on an independent, real-field test set
Handle low-confidence predictions and unsupported crop images
Add more crops and diseases
Multilingual support (Hindi) for farmers
Better mobile responsiveness
Deployment with logging and monitoring
Disclaimer

KisanSmart is an educational project. AI predictions are preliminary and may be wrong. Please confirm disease identification and treatment with a qualified agricultural expert.

Author

Chandra Prakash Patidar B.Tech, Computer Science & Engineering GitHub: aryaPATIDAR

<div align="center">

KisanSmart: bringing AI-assisted insights closer to farmers.

</div>
