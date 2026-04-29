from flask import Flask, render_template

app = Flask(__name__)

# 🏠 Home Page
@app.route("/")
def home():
    data = {
        "crop": "Wheat",
        "status": "Healthy",
        "moisture": "70%",
        "temperature": "28°C"
    }
    return render_template("index.html", data=data)




# 🌱 Disease Prediction Page
@app.route("/disease")
def disease():
    return render_template("disease.html")


# 🌦 Weather Page
@app.route("/weather")
def weather():
    return render_template("weather.html")


# 👨‍🌾 Farmer Page
@app.route("/farmer")
def farmer():
    return render_template("farmer.html")


# 🛒 Trader Page
@app.route("/trader")
def trader():
    return render_template("trader.html")


if __name__ == "__main__":
    app.run(debug=True)