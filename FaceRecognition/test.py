import pickle

with open("FaceRecognition/EncodeFile.p", "rb") as file:
    encodeListKnown, studentIds = pickle.load(file)

print("Number of encodings:", len(encodeListKnown))
print("Student IDs:", studentIds)