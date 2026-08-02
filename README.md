# KisanSmart

A web app I built for farmers and traders to access AI-based agriculture tools in one place. Made using Flask, with separate login flows for two types of users — Kisan (farmer) and Vyapari (trader).

## What it does

- Farmers and traders log in separately with role-based access, so each sees a different dashboard based on what they need
- Login is OTP-based instead of just password, for extra security
- Each user gets a unique ID when they sign up
- Crop disease detection — upload a photo of your crop and it tells you if something's wrong
- Weather forecast built in, so farmers can plan their work accordingly
- Basic soil analysis feature to help with crop planning
- Simple UI with a hero image slideshow on the homepage, and the navbar changes depending on whether you're logged in as farmer or trader

## Built with

- Python + Flask (backend)
- HTML/CSS/JS (frontend)
- SQLite for the database

## How to run it locally

\```bash
git clone https://github.com/yourusername/KisanSmart.git
cd KisanSmart
pip install -r requirements.txt
python app.py
\```

Then open `http://localhost:5000` in your browser.

## Why I built this

Wanted to work on something that combined web dev with AI, and agriculture felt like a space where tech could actually make a difference for people who don't usually get access to it.

---
