
import os
from pymongo import MongoClient
import certifi
import sys

# Try with Admin123
uri = "mongodb+srv://Admin:Admin123@complaintsystem.4l7kqvq.mongodb.net/?appName=ComplaintSystem"

print(f"Attempting to connect with Admin:Admin123...")
try:
    client = MongoClient(uri, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("✅ Success! 'Admin123' is the correct password.")
    # List collections to be sure
    db = client['smart_complaint_system']
    print(f"Collections: {db.list_collection_names()}")
    sys.exit(0)
except Exception as e:
    print(f"❌ Failed with Admin123: {e}")

# If we are here, it failed. The user also said "or admin123" but we already tried that and it failed. 
# Just in case, let's try 'admin' (lowercase user) with both passwords if the above fails? 
# The user specified "username Admin", so let's stick to that for now.
# But maybe the username is case sensitive and it's 'admin'?
# Let's try 'admin:admin123' and 'admin:Admin123' just in case 'Admin' is wrong.

candidates = [
    ("admin", "admin123"),
    ("admin", "Admin123"),
    ("Admin", "admin123") # Retrying this just in case
]

for user, pwd in candidates:
    print(f"\nAttempting with {user}:{pwd}...")
    try:
        uri = f"mongodb+srv://{user}:{pwd}@complaintsystem.4l7kqvq.mongodb.net/?appName=ComplaintSystem"
        client = MongoClient(uri, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print(f"✅ Success! Correct credentials are {user}:{pwd}")
        sys.exit(0)
    except Exception as e:
         print(f"❌ Failed: {e}")

print("\n❌ All attempts failed.")
sys.exit(1)
