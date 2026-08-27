from database import _get_mongo_connection
import os
from dotenv import load_dotenv

load_dotenv()

def check_complaint_2():
    try:
        mongo = _get_mongo_connection()
        doc = mongo.complaints.find_one({'id': 2})
        if doc:
            print(f"Complaint #2 Status: {doc.get('status')}")
            print(f"Admin Response: {doc.get('admin_response')}")
            print(f"Category: {doc.get('category')}")
            print(f"Priority: {doc.get('priority')}")
            print(f"Assigned To: {doc.get('assigned_to')}")
            print(f"Updated At: {doc.get('updated_at')}")
        else:
            print("Complaint #2 not found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_complaint_2()
