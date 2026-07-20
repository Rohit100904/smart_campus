# ==========================================================
# SMART CAMPUS
# Encode Generator
# ==========================================================

import os
import cv2
import pickle
import face_recognition

# ==========================================================
# Paths
# ==========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

IMAGE_FOLDER = os.path.join(BASE_DIR, "Images")

ENCODE_FILE = os.path.join(BASE_DIR, "EncodeFile.p")

# ==========================================================
# Load Images
# ==========================================================

imageList = []

studentIds = []

print("Loading Images...")

for filename in os.listdir(IMAGE_FOLDER):

    path = os.path.join(IMAGE_FOLDER, filename)

    image = cv2.imread(path)

    if image is None:

        continue

    imageList.append(image)

    studentIds.append(os.path.splitext(filename)[0])

print(f"{len(imageList)} Images Loaded")

# ==========================================================
# Encode Images
# ==========================================================

def findEncodings(images):

    encodeList = []

    for index, img in enumerate(images):

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        encodings = face_recognition.face_encodings(rgb)

        if len(encodings) > 0:

            encodeList.append(encodings[0])

            print(f"Face found in {studentIds[index]}")

        else:

            print(f"No face detected in {studentIds[index]}")

    return encodeList

print("Encoding Faces...")

encodeListKnown = findEncodings(imageList)

print("Encoding Complete")

# ==========================================================
# Save Encodings
# ==========================================================

with open(ENCODE_FILE, "wb") as file:

    pickle.dump(

        [encodeListKnown, studentIds],

        file

    )

print("EncodeFile.p Generated Successfully")