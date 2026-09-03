
import os
from dotenv import load_dotenv
from database import MongoDBWrapper, _get_mongo_connection
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

# Setup pure DB test
print("Initializing DB...")
mongo_conn = _get_mongo_connection()
db = MongoDBWrapper(mongo_conn)

complaint_id = 2
status = "In Progress"
admin_response = "Testing update script"

print(f"Attempting update for ID {complaint_id}...")

# Original SQL from routes.py
sql = "UPDATE complaints SET status = ?, admin_response = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
params = (status, admin_response, complaint_id)

try:
    print(f"Executing: {sql} with params {params}")
    
    # We want to see logs from database.py too, which use logging.getLogger(__name__)
    # So basicConfig should handle it.
    
    db.execute(sql, params)
    print("Execute finished.")
    
    # Verify update
    c = db.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    if c:
        print(f"Updated record: Status={c['status']}, Response={c['admin_response']}")
    else:
        print("Record not found!")
    
except Exception as e:
    print(f"Update failed: {e}")
