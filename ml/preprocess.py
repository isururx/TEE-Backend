from io import BytesIO

import numpy as np
from PIL import Image
from tensorflow.keras.applications.efficientnet import preprocess_input


IMAGE_SIZE = (224, 224)


def preprocess_image(image_bytes):

    image = Image.open(BytesIO(image_bytes))

    image = image.convert("RGB")

    image = image.resize(IMAGE_SIZE)

    image = np.array(image, dtype=np.float32)

    image = preprocess_input(image)

    image = np.expand_dims(image, axis=0)

    return image