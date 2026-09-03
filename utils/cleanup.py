import os
import time
import sqlite3
from datetime import datetime, timedelta

def cleanup_old_audio(days=30):
    """
    Deletes audio files older than the specified number of days.
    Also updates the database to reflect that the audio has been deleted for privacy.
    """
    db_path = os.path.join(os.getcwd(), 'complaints.db')
    upload_folder = os.path.join(os.getcwd(), 'uploads', 'complaints', 'audio')
    
    if not os.path.exists(upload_folder):
        print("[Cleanup] Audio folder does not exist.")
        return

    cutoff_date = datetime.now() - timedelta(days=days)
    print(f"[Cleanup] Looking for audio files older than {cutoff_date}...")

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        db = conn.cursor()

        # Find complaints with audio files older than cutoff
        query = "SELECT id, audio_file FROM complaints WHERE audio_file IS NOT NULL AND created_at < ?"
        db.execute(query, (cutoff_date.strftime('%Y-%m-%d %H:%M:%S'),))
        old_complaints = db.fetchall()

        deleted_count = 0
        for complaint in old_complaints:
            file_path = os.path.join(upload_folder, complaint['audio_file'])
            
            # 1. Delete the physical file
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"[Cleanup] Deleted file: {complaint['audio_file']}")
                except Exception as e:
                    print(f"[Cleanup Error] Could not delete file {file_path}: {e}")

            # 2. Update DB to Null (or a 'Deleted' placeholder)
            db.execute("UPDATE complaints SET audio_file = NULL WHERE id = ?", (complaint['id'],))
            deleted_count += 1

        conn.commit()
        conn.close()
        print(f"[Cleanup] Successfully cleaned up {deleted_count} audio recordings.")

    except Exception as e:
        print(f"[Cleanup Error] Database operation failed: {e}")

if __name__ == "__main__":
    # Can be run manually or as a cron job
    cleanup_old_audio(days=30)
