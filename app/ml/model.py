import numpy as np
from tensorflow.keras.models import load_model


MODEL_PATH = "app/models/tee_leaf_model.keras"

model = load_model(MODEL_PATH)


CLASS_NAMES = [
    "Brown Blight",
    "Gray Blight",
    "Green mirid bug",
    "Healthy leaf",
    "Helopeltis",
    "Red spider",
    "Tea algal leaf spot"
]


def predict_image(image):

    prediction = model.predict(image, verbose=0)

    class_index = int(np.argmax(prediction[0]))

    confidence = float(prediction[0][class_index])

    disease_name = CLASS_NAMES[class_index]

    print("Prediction probabilities:", prediction[0])
    print("Predicted class index:", class_index)
    print("Predicted class:", disease_name)
    print("Confidence:", confidence)

    return disease_name, confidence