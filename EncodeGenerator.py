import os
import cv2
import face_recognition
import pickle
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import storage

# Initialize Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': "https://faceattendencerealtime-8a7a2-default-rtdb.firebaseio.com/",
    'storageBucket': "faceattendencerealtime-8a7a2.appspot.com"
})

# Import student images
folderPath = 'Images'
pathList = os.listdir(folderPath)
print("Images found:", pathList)

imgList = []
studentIds = []

for path in pathList:
    fullPath = os.path.join(folderPath, path)
    img = cv2.imread(fullPath)

    if img is None:
        print(f"❗ Error loading image: {fullPath} — Skipping this file.")
        continue

    imgList.append(img)
    studentIds.append(os.path.splitext(path)[0])

    # Upload to Firebase Storage
    try:
        bucket = storage.bucket()
        blob = bucket.blob(f'Images/{path}')
        blob.upload_from_filename(fullPath)
        print(f"Uploaded: {path}")
    except Exception as e:
        print(f"Upload error for {path}: {e}")

print("Student IDs:", studentIds)


# ---------------------------
# Function to encode faces
# ---------------------------
def findEncodings(imagesList):
    encodeList = []
    for index, img in enumerate(imagesList):

        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        faceLocs = face_recognition.face_locations(imgRGB)

        if len(faceLocs) == 0:
            print(f"❗ No face found in image index {index}")
            continue

        try:
            encode = face_recognition.face_encodings(imgRGB, faceLocs)[0]
            encodeList.append(encode)
            print(f"✔ Encoded Image Index {index}")
        except:
            print(f"❗ Encoding failed at image index {index}")

    return encodeList



print("\nEncoding Started...")
encodeListKnown = findEncodings(imgList)
encodeListKnownWithIds = [encodeListKnown, studentIds]
print("Encoding Complete.")

# Save encodings file
with open("EncodeFile.p", 'wb') as file:
    pickle.dump(encodeListKnownWithIds, file)

print("EncodeFile.p Saved Successfully!")
