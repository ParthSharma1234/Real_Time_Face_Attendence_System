import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred,{
    'databaseURL':"https://faceattendencerealtime-8a7a2-default-rtdb.firebaseio.com/"
})

ref = db.reference('Students')

data = {
    "321654":
        {
            "name":"Parth Sharma",
            "major":"IT",
            "starting_year":"2022",
            "total_attendance":10,
            "standing":"G",
            "year":4,
            "last_attendance_time":"2022-12-11 00:54:34"
        },
    "741852":
        {
            "name":"Emly Blunt",
            "major":"Economics",
            "starting_year":"2023",
            "total_attendance":12,
            "standing":"B",
            "year":1,
            "last_attendance_time":"2022-12-11 00:54:34"
        },
    "963852":
        {
            "name":"Elon Musk",
            "major":"CS",
            "starting_year":"2024",
            "total_attendance":7,
            "standing":"G",
            "year":2,
            "last_attendance_time":"2022-12-11 00:54:34"
        },
    "111111":
        {
            "name":"Vin Diesel",
            "major":"IT",
            "starting_year":"2025",
            "total_attendance":0,
            "standing":"A",
            "year":3,
            "last_attendance_time":"2022-12-11 00:54:34"
        },
}
#To send a data to specific directory
for key,value in data.items():
    ref.child(key).set(value)

