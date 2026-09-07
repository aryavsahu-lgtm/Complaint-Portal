import os
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('AutomatedAssistant')

# Get absolute path to the database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'mineguard.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def escalate_old_issues():
    """Background job that scans for stuck complaints and auto-escalates them."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # We consider a complaint "stuck" if it's Pending and older than 24 hours
        time_threshold = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
        
        cur.execute("""
            SELECT id, title, created_at, is_escalated 
            FROM complaints 
            WHERE status = 'Pending' AND is_escalated = 0 AND created_at < ?
        """, (time_threshold,))
        stuck_complaints = cur.fetchall()
        
        if stuck_complaints:
            logger.info(f"Found {len(stuck_complaints)} stuck complaints to escalate.")
            
            for comp in stuck_complaints:
                # Update the complaint
                cur.execute("""
                    UPDATE complaints 
                    SET is_escalated = 1, priority = 'High', updated_at = ?
                    WHERE id = ?
                """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), comp['id']))
                
                # Log to audit ledger
                details = f"Auto-escalated complaint #{comp['id']} ('{comp['title']}') - Unresolved for > 24 hours."
                cur.execute("""
                    INSERT INTO audit_logs (user_id, action, details, created_at)
                    VALUES ('SYSTEM', 'AUTO_ESCALATE', ?, ?)
                """, (details, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                
            conn.commit()
            logger.info("Auto-escalation complete.")
        else:
            logger.info("No stuck complaints found.")
            
    except Exception as e:
        logger.error(f"Error in background task: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def start_scheduler():
    scheduler = BackgroundScheduler()
    # In production, run this every hour. For demo, we run it every minute.
    scheduler.add_job(escalate_old_issues, 'interval', minutes=1)
    scheduler.start()
    logger.info("APScheduler started: automated assistant is running in background.")
