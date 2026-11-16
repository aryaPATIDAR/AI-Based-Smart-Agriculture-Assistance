from flask import Flask

from backend.core.config import (
    SECRET_KEY,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET
)

from backend.core.oauth import init_oauth

from backend.database.db import engine
from backend.database.models import Base

from backend.routes.auth import auth_bp
from backend.routes.home import home_bp
from backend.routes.disease import disease_bp
from backend.routes.farmer import farmer_bp
from backend.routes.trader import trader_bp
from backend.routes.weather import weather_bp
from backend.routes.admin import admin_bp

app = Flask(__name__)

app.secret_key = SECRET_KEY

app.config["GOOGLE_CLIENT_ID"] = GOOGLE_CLIENT_ID
app.config["GOOGLE_CLIENT_SECRET"] = GOOGLE_CLIENT_SECRET

init_oauth(app)

for bp in (auth_bp, home_bp, disease_bp, farmer_bp, trader_bp, weather_bp, admin_bp):
    app.register_blueprint(bp)

Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")