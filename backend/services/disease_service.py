import tensorflow as tf
import numpy as np
from PIL import Image
import io

# load model once (IMPORTANT)
model = None

try:
    model = tf.keras.models.load_model("models/model.h5")
except:
    print("⚠️ Model not found, running in dummy mode")

# classes (customize later)
classes = ["Healthy", "Leaf Blight", "Rust", "Powdery Mildew"]

# solution mapping
solutions = {
    "Leaf Blight": "Use fungicide spray",
    "Rust": "Apply sulfur-based fungicide",
    "Powdery Mildew": "Use neem oil spray",
    "Healthy": "No action needed"
}

precautions = {
    "Leaf Blight": "Avoid excess moisture",
    "Rust": "Ensure proper air circulation",
    "Powdery Mildew": "Avoid overcrowding plants",
    "Healthy": "Maintain regular care"
}


async def predict_disease(file):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    image = image.resize((224, 224))

    img_array = np.array(image) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    # 🔥 If model exists → use AI
    if model:
        prediction = model.predict(img_array)
        class_index = np.argmax(prediction)
        confidence = float(np.max(prediction) * 100)
        disease = classes[class_index]

    # ⚠️ fallback (dummy logic)
    else:
        disease = "Leaf Blight"
        confidence = 85.0

    return {
        "disease": disease,
        "confidence": round(confidence, 2),
        "solution": solutions.get(disease, "Consult expert"),
        "precaution": precautions.get(disease, "General care")
    }