import os
import io
import json
import logging

import numpy as np
from PIL import Image

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import tensorflow as tf

logger = logging.getLogger(__name__)

# =========================================================
# PATH CONFIGURATION
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODELS_DIR = os.path.abspath(
    os.path.join(BASE_DIR, "..", "models")
)

MODEL_KERAS_PATH = os.path.join(
    MODELS_DIR, "crop_disease_model.keras"
)

MODEL_H5_PATH = os.path.join(
    MODELS_DIR, "model.h5"
)

CLASS_INDICES_PATH = os.path.join(
    MODELS_DIR, "class_indices.json"
)

METADATA_PATH = os.path.join(
    MODELS_DIR, "disease_metadata.json"
)


# =========================================================
# KERAS COMPATIBILITY FIX
# =========================================================

class CompatibleGlorotUniform(tf.keras.initializers.GlorotUniform):
    """
    Handles older/newer Keras serialized GlorotUniform configs.

    Some saved models contain input_axes and output_axes,
    which current Keras GlorotUniform does not accept.
    """

    def __init__(
        self,
        seed=None,
        input_axes=None,
        output_axes=None,
        **kwargs
    ):
        self.input_axes = input_axes
        self.output_axes = output_axes

        # Current Keras initializer accepts seed.
        super().__init__(seed=seed)


CUSTOM_OBJECTS = {
    "GlorotUniform": CompatibleGlorotUniform,
    "keras.initializers>GlorotUniform": CompatibleGlorotUniform,
    "keras>GlorotUniform": CompatibleGlorotUniform,
}


# =========================================================
# CROP ALIASES
# =========================================================

CROP_ALIAS_MAP = {
    "gehu": "Wheat",
    "wheat": "Wheat",

    "dhan": "Rice",
    "rice": "Rice",
    "paddy": "Rice",

    "tamatar": "Tomato",
    "tomato": "Tomato",

    "aalu": "Potato",
    "aloo": "Potato",
    "potato": "Potato",

    "kapas": "Cotton",
    "cotton": "Cotton",

    "soyabean": "Soybean",
    "soybean": "Soybean",
}


# =========================================================
# GLOBAL MODEL VARIABLES
# =========================================================

_model = None
_classes = []
_metadata = {}


# =========================================================
# MODEL LOADING
# =========================================================

def get_model():

    global _model, _classes, _metadata

    if _model is not None:
        return _model, _classes, _metadata

    # -----------------------------------------------------
    # Load class indices
    # -----------------------------------------------------

    if not os.path.exists(CLASS_INDICES_PATH):
        raise RuntimeError(
            f"Class indices file not found: {CLASS_INDICES_PATH}"
        )

    try:
        with open(
            CLASS_INDICES_PATH,
            "r",
            encoding="utf-8"
        ) as f:

            indices_data = json.load(f)

            _classes = indices_data.get("classes", [])

    except Exception as e:
        raise RuntimeError(
            f"Could not read class_indices.json: {e}"
        ) from e

    if not _classes:
        raise RuntimeError(
            "Class mapping is empty."
        )

    # -----------------------------------------------------
    # Load disease metadata
    # -----------------------------------------------------

    if os.path.exists(METADATA_PATH):

        try:
            with open(
                METADATA_PATH,
                "r",
                encoding="utf-8"
            ) as f:

                _metadata = json.load(f)

        except Exception as e:
            logger.warning(
                "Disease metadata could not be loaded: %s", e
            )

            _metadata = {}

    # -----------------------------------------------------
    # Load trained model
    # -----------------------------------------------------

    model_paths = [
        MODEL_KERAS_PATH,
        MODEL_H5_PATH
    ]

    load_errors = []

    for model_path in model_paths:

        if not os.path.exists(model_path):
            continue

        if os.path.getsize(model_path) <= 1000:

            load_errors.append(
                f"{model_path}: Model file is too small."
            )

            continue

        try:

            logger.info(
                "Loading AI model: %s", model_path
            )



            with tf.keras.utils.custom_object_scope(CUSTOM_OBJECTS):
                loaded_model = tf.keras.models.load_model(
                    model_path,
                    compile=False,
                    custom_objects=CUSTOM_OBJECTS
                )

            # -------------------------------------------------
            # Validate model output
            # -------------------------------------------------

            output_shape = loaded_model.output_shape

            if isinstance(output_shape, list):
                raise RuntimeError(
                    "Multiple model outputs are not supported."
                )

            output_classes = output_shape[-1]

            if output_classes != len(_classes):

                raise RuntimeError(
                    f"Model output classes ({output_classes}) "
                    f"do not match class mapping ({len(_classes)})."
                )

            _model = loaded_model

            logger.info(
                "AI model loaded successfully: %s",
                model_path
            )

            logger.info(
                "Total supported disease classes: %d",
                len(_classes)
            )

            return _model, _classes, _metadata

        except Exception as e:

            load_errors.append(
                f"{model_path}: {str(e)}"
            )

            logger.exception(
                "Failed to load model: %s", model_path
            )

    error_details = "\n".join(load_errors)

    raise RuntimeError(
        "AI model could not be loaded.\n"
        f"Model loading errors:\n{error_details}"
    )


# =========================================================
# CROP NAME NORMALIZATION
# =========================================================

def normalize_crop_name(name: str) -> str:

    if not name:
        return "Wheat"

    clean = str(name).strip().lower()

    return CROP_ALIAS_MAP.get(clean, "Wheat")


# =========================================================
# DISEASE PREDICTION
# =========================================================

def predict_disease_sync(
    contents: bytes,
    crop_hint: str = None
) -> dict:

    """
    Validates an uploaded leaf image and performs
    disease prediction using the trained MobileNetV2 model.

    Supported crops:
    Wheat, Rice, Tomato, Potato, Cotton, Soybean.
    """

    # -----------------------------------------------------
    # 1. Validate image contents
    # -----------------------------------------------------

    if not contents:

        raise ValueError(
            "Khali photo upload ki gayi hai."
        )

    try:

        verify_img = Image.open(
            io.BytesIO(contents)
        )

        verify_img.verify()

    except Exception as e:

        raise ValueError(
            "File valid photo nahi hai ya corrupt hai."
        ) from e

    # -----------------------------------------------------
    # 2. Convert image to RGB
    # -----------------------------------------------------

    try:

        image = Image.open(
            io.BytesIO(contents)
        ).convert("RGB")

    except Exception as e:

        raise ValueError(
            "Photo process karne mein dikkat aayi."
        ) from e

    # -----------------------------------------------------
    # 3. Resize image to 224x224
    # -----------------------------------------------------

    image = image.resize(
        (224, 224),
        Image.Resampling.BILINEAR
    )

    img_array = np.array(
        image,
        dtype=np.float32
    )

    # MobileNetV2 normalization: [-1, 1]

    img_array = (
        img_array / 127.5
    ) - 1.0

    img_tensor = np.expand_dims(
        img_array,
        axis=0
    )

    # -----------------------------------------------------
    # 4. Load trained model
    # -----------------------------------------------------

    model, classes, metadata = get_model()

    # -----------------------------------------------------
    # 5. Model inference
    # -----------------------------------------------------

    preds = model.predict(
        img_tensor,
        verbose=0
    )[0]

    preds = np.asarray(
        preds,
        dtype=np.float64
    )

    if (
        len(preds) != len(classes)
        or not np.all(np.isfinite(preds))
    ):

        raise RuntimeError(
            "Model returned invalid prediction values."
        )

    # -----------------------------------------------------
    # 6. Crop-conditioned prediction
    # -----------------------------------------------------

    norm_crop = normalize_crop_name(
        crop_hint
    )

    crop_prefix = f"{norm_crop}___"

    matching_indices = [
        i
        for i, class_name in enumerate(classes)
        if class_name.startswith(crop_prefix)
    ]

    if matching_indices:

        sub_probs = preds[matching_indices]

        sum_p = np.sum(sub_probs)

        if sum_p > 1e-7:

            norm_sub_probs = (
                sub_probs / sum_p
            )

        else:

            raise RuntimeError(
                "Invalid probabilities for selected crop."
            )

        best_sub_idx = int(
            np.argmax(norm_sub_probs)
        )

        predicted_idx = matching_indices[
            best_sub_idx
        ]

        confidence = float(
            norm_sub_probs[best_sub_idx] * 100.0
        )

    else:

        predicted_idx = int(
            np.argmax(preds)
        )

        confidence = float(
            np.max(preds) * 100.0
        )

    # -----------------------------------------------------
    # 7. Extract prediction details
    # -----------------------------------------------------

    predicted_class = classes[predicted_idx]

    meta = metadata.get(
        predicted_class,
        {}
    )

    crop_name = meta.get(
        "crop",
        norm_crop
    )

    local_crop = meta.get(
        "local_crop",
        crop_name
    )

    disease_name = meta.get(
        "disease",
        predicted_class.split("___")[-1].replace("_", " ")
    )

    local_disease = meta.get(
        "local_disease",
        disease_name
    )

    severity = meta.get(
        "severity",
        "Low" if disease_name == "Healthy" else "Medium"
    )

    severity_pct = meta.get(
        "severity_pct",
        0 if disease_name == "Healthy" else 65
    )

    bachne_ka_chance = meta.get(
        "bachne_ka_chance",
        100 if disease_name == "Healthy" else 60
    )

    symptoms = meta.get(
        "symptoms",
        "Patti par bimari ke lakshan dikh rahe hain."
    )

    solution = meta.get(
        "solution",
        "Uchit fafundinashak ka chhidkaw karein."
    )

    precaution = meta.get(
        "precaution",
        "Khet ki niyamit jaanch karein aur safayi banaye rakhein."
    )

    # -----------------------------------------------------
    # 8. Return result
    # -----------------------------------------------------

    return {

        "crop": crop_name,

        "local_crop": local_crop,

        "disease": disease_name,

        "local_disease": local_disease,

        "full_class": predicted_class,

        "confidence": round(
            confidence,
            2
        ),

        "severity": severity,

        "severity_pct": int(
            severity_pct
        ),

        "bachne_ka_chance": int(
            bachne_ka_chance
        ),

        "symptoms": symptoms,

        "solution": solution,

        "precaution": precaution,

    }