
import os
from pymongo import MongoClient
import certifi
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv('MONGO_URI')
client = MongoClient(uri, tlsCAFile=certifi.where())
db = client[os.getenv('MONGO_DB_NAME', 'smart_complaint_system')]

print("checking types...")
for c in db.complaints.find():
    cid = c.get('id')
    print(f"Complaint ID: {cid}, Type: {type(cid)}")
