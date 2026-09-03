from database import get_db, _get_mongo_connection
import os
from dotenv import load_dotenv
from flask import Flask

load_dotenv()
app = Flask(__name__)

def check_ids():
    with app.app_context():
        try:
            db_conn = _get_mongo_connection()
            print("Connected to MongoDB")
            complaints = list(db_conn.complaints.find({}))
            if not complaints:
                print("No complaints found.")
                return
            for c in complaints:
                c_id = c.get('id')
                print(f"Complaint _id: {c.get('_id')} | id field: {c_id} (Type: {type(c_id)})")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_ids()
