import os
import pickle
from datetime import datetime
import cv2
import cvzone
import face_recognition
import numpy as np
import firebase_admin
from firebase_admin import credentials, db, storage

# Initialize Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': "https://faceattendencerealtime-8a7a2-default-rtdb.firebaseio.com/",
    'storageBucket': "faceattendencerealtime-8a7a2.appspot.com"
})

bucket = storage.bucket()

# Open webcam
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("Could not open webcam (VideoCapture(0)).")

cap.set(3, 640)
cap.set(4, 480)

imgBackground = cv2.imread('Resources/background.png')
if imgBackground is None:
    raise FileNotFoundError("Resources/background.png not found.")

# Importing the mode images into a list
folderModePath = 'Resources/Modes'
modePathList = os.listdir(folderModePath)
imgModeList = [cv2.imread(os.path.join(folderModePath, p)) for p in modePathList]

# Load encoding file
print("Loading Encoded File...")
with open('EncodeFile.p', 'rb') as f:
    encodeListKnownWithIds = pickle.load(f)

encodeListKnown, studentIds = encodeListKnownWithIds
print("Encode File Loaded. Known encodings:", len(encodeListKnown))

modeType = 0
counter = 0
student_id = None
imgStudent = None
studentInfo = None

while True:
    success, img = cap.read()
    if not success:
        print("Failed to read frame from webcam. Exiting loop.")
        break

    # Resize & convert for faster processing
    imgS = cv2.resize(img, (0, 0), fx=0.25, fy=0.25)
    imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

    # detect faces in the small frame
    faceCurFrame = face_recognition.face_locations(imgS)
    encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)

    # place webcam image & mode overlay on background
    try:
        imgBackground[162:162 + 480, 55:55 + 640] = img
    except Exception as e:
        # If overlay slice fails (size mismatch), skip overlay for this frame
        print("Warning: overlay webcam on background failed:", e)

    # ensure mode image exists before placing
    if 0 <= modeType < len(imgModeList):
        try:
            imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
        except Exception as e:
            print("Warning: overlay mode image failed:", e)

    if faceCurFrame and encodeCurFrame:
        for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
            # if no known encodings, skip matching
            if len(encodeListKnown) == 0:
                continue

            # compare to known encodings
            matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)

            if len(faceDis) == 0:
                continue

            matchIndex = np.argmin(faceDis)
            # print("Match Index", matchIndex)

            if matches[matchIndex]:
                y1, x2, y2, x1 = faceLoc
                # scale back to original size (we processed 1/4 scaled image)
                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                bbox = (55 + x1, 162 + y1, x2 - x1, y2 - y1)
                imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)

                student_id = studentIds[matchIndex]

                if counter == 0:
                    counter = 1
                    modeType = 1

        # after detecting a recognized face, fetch info once and show popup
        if counter != 0:
            if counter == 1 and student_id is not None:
                # get student data from realtime DB
                try:
                    studentInfo = db.reference(f'Students/{student_id}').get()
                    if not studentInfo:
                        print(f"No student data found for id {student_id}.")
                        # reset and continue
                        modeType = 0
                        counter = 0
                        student_id = None
                        continue
                except Exception as e:
                    print("Firebase DB read error:", e)
                    modeType = 0
                    counter = 0
                    student_id = None
                    continue

                # get student image from storage
                try:
                    blob = bucket.get_blob(f'Images/{student_id}.png')
                    if blob is None:
                        print(f"No blob found for Images/{student_id}.png")
                        imgStudent = np.zeros((216, 216, 3), dtype=np.uint8)  # placeholder
                    else:
                        array = np.frombuffer(blob.download_as_string(), np.uint8)
                        imgStudent = cv2.imdecode(array, cv2.IMREAD_COLOR)
                        if imgStudent is None:
                            imgStudent = np.zeros((216, 216, 3), dtype=np.uint8)
                except Exception as e:
                    print("Firebase storage error:", e)
                    imgStudent = np.zeros((216, 216, 3), dtype=np.uint8)

                # check last attendance and update if allowed
                try:
                    last_time_str = studentInfo.get('last_attendance_time', None)
                    if last_time_str:
                        datetimeObject = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
                        secondsElapsed = (datetime.now() - datetimeObject).total_seconds()
                    else:
                        secondsElapsed = float('inf')

                    if secondsElapsed > 30:
                        ref = db.reference(f'Students/{student_id}')
                        # increment safely
                        total = studentInfo.get('total_attendance', 0) + 1
                        ref.child('total_attendance').set(total)
                        ref.child('last_attendance_time').set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        studentInfo['total_attendance'] = total
                    else:
                        modeType = 3
                        counter = 0
                        imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
                except Exception as e:
                    print("Error updating attendance:", e)
                    modeType = 0
                    counter = 0
                    student_id = None
                    studentInfo = None

            # show student info popup animation
            if modeType != 3 and studentInfo:
                if 10 < counter < 20:
                    modeType = 2

                # make sure mode overlay exists
                try:
                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
                except Exception:
                    pass

                if counter <= 10:
                    # draw text fields (use .get to avoid KeyError)
                    cv2.putText(imgBackground, str(studentInfo.get('total_attendance', 'N/A')), (861, 125),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(studentInfo.get('major', '')), (1006, 550),
                                cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(student_id), (1006, 493),
                                cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(studentInfo.get('standing', '')), (910, 625),
                                cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                    cv2.putText(imgBackground, str(studentInfo.get('year', '')), (1025, 625),
                                cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                    cv2.putText(imgBackground, str(studentInfo.get('starting_year', '')), (1125, 625),
                                cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)

                    name = str(studentInfo.get('name', ''))
                    (w, h), _ = cv2.getTextSize(name, cv2.FONT_HERSHEY_COMPLEX, 1, 1)
                    offset = (414 - w) // 2
                    cv2.putText(imgBackground, name, (808 + offset, 445),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 50), 1)

                    # place student image safely (ensure sizes match)
                    try:
                        imgBackground[175:175 + 216, 909:909 + 216] = cv2.resize(imgStudent, (216, 216))
                    except Exception:
                        pass

                counter += 1

                if counter >= 20:
                    counter = 0
                    modeType = 0
                    studentInfo = None
                    imgStudent = None
                    student_id = None
                    try:
                        imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
                    except Exception:
                        pass
    else:
        # no face in frame
        modeType = 0
        counter = 0
        student_id = None
        studentInfo = None
        imgStudent = None

    cv2.imshow("Face Attendance", imgBackground)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# cleanup
cap.release()
cv2.destroyAllWindows()
