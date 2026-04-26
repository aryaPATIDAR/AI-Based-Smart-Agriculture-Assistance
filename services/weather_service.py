from dotenv import load_dotenv
import os
import requests

load_dotenv()

API_KEY = os.getenv("API_KEY")

def get_weather(city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()

        if "main" not in data:
            return {"error": data}

        temp = data["main"]["temp"]
        rain = data.get("rain", {}).get("1h", 0)

        advice = "Avoid irrigation" if rain > 0 else "Safe to irrigate"

        return {
            "temperature": temp,
            "rain": rain,
            "advice": advice
        }

    except Exception as e:
        return {"error": str(e)}