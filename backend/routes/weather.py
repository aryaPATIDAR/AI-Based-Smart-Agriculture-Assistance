from flask import Blueprint, render_template

weather_bp = Blueprint("weather", __name__)


@weather_bp.route("/weather")
def weather():
    return render_template("weather.html")