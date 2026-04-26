from fastapi import FastAPI, File, UploadFile
from services.disease_service import predict_disease
from services.weather_service import get_weather

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Smart Agriculture API Running"}

@app.post("/predict-disease")
async def disease(file: UploadFile = File(...)):
    result = await predict_disease(file)
    return result

@app.get("/weather")
def weather(city: str):
    return get_weather(city)