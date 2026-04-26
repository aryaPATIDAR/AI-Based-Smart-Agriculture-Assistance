from PIL import Image
import io

async def predict_disease(file):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))

    # Dummy prediction (we replace later with ML)
    return {
        "disease": "Leaf Blight",
        "confidence": 90,
        "solution": "Use fungicide spray"
    }