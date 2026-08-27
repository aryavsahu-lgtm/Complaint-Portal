"""
Performance Optimization Script for Smart Complaint System
Adds missing database indexes to speed up queries
"""
import sqlite3

def optimize_database(db_path='complaints.db'):
    """Add performance indexes to the database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🚀 Starting Performance Optimization...")
    
    # Add indexes for home page statistics queries
    indexes = [
        # For city-wise statistics
        ("CREATE INDEX IF NOT EXISTS idx_complaints_city ON complaints(city)", "City index"),
        
        # For resolution time queries
        ("CREATE INDEX IF NOT EXISTS idx_complaints_resolved_at ON complaints(resolved_at)", "Resolved date index"),
        
        # For rating queries
        ("CREATE INDEX IF NOT EXISTS idx_complaints_rating ON complaints(rating)", "Rating index"),
        
        # For worker allocation queries
        ("CREATE INDEX IF NOT EXISTS idx_workers_active ON workers(is_active)", "Active workers index"),
        ("CREATE INDEX IF NOT EXISTS idx_workers_skill ON workers(skill)", "Worker skills index"),
        
        # For chat session queries
        ("CREATE INDEX IF NOT EXISTS idx_chat_history_session ON chat_history(session_id)", "Chat session index"),
        
        # Composite index for common complaint queries
        ("CREATE INDEX IF NOT EXISTS idx_complaints_user_status ON complaints(user_id, status)", "User status composite index"),
        
        # For reference number lookups
        ("CREATE INDEX IF NOT EXISTS idx_complaints_ref_no ON complaints(ref_no)", "Reference number index"),
    ]
    
    for sql, description in indexes:
        try:
            cursor.execute(sql)
            print(f"✅ Added: {description}")
        except Exception as e:
            print(f"⚠️  Failed to add {description}: {e}")
    
    conn.commit()
    conn.close()
    print("\n✨ Performance optimization complete!\n")

if __name__ == '__main__':
    optimize_database()
