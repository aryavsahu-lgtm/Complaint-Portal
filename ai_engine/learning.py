import sqlite3
from datetime import datetime

class LearningEngine:
    """
    Step 11: Learning & Optimization Layer
    Updates technician performance metrics based on resolved tasks.
    """
    
    @staticmethod
    def update_technician_metrics(worker_id, resolution_time_minutes, rating):
        """
        Updates avg_resolution_time and performance_rating using a moving average.
        """
        if not worker_id: return
        
        conn = sqlite3.connect('complaints.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Fetch current metrics
        worker = cursor.execute("SELECT avg_resolution_time, performance_rating FROM workers WHERE id = ?", (worker_id,)).fetchone()
        
        if not worker:
            conn.close()
            return

        # Simple Reinforcement: Update metrics using weighted average (Learning Rate = 0.2)
        LEARNING_RATE = 0.2
        
        # 1. Update Resolution Time
        current_avg_time = worker['avg_resolution_time'] or 30.0 # Fallback
        new_avg_time = (current_avg_time * (1 - LEARNING_RATE)) + (resolution_time_minutes * LEARNING_RATE)
        
        # 2. Update Performance Rating
        current_rating = worker['performance_rating'] or 5.0
        new_rating = (current_rating * (1 - LEARNING_RATE)) + (rating * LEARNING_RATE)
        
        # 3. Update Database
        cursor.execute('''
            UPDATE workers 
            SET avg_resolution_time = ?, 
                performance_rating = ?,
                current_load = MAX(0, current_load - 1)
            WHERE id = ?
        ''', (round(new_avg_time, 2), round(new_rating, 2), worker_id))
        
        conn.commit()
        conn.close()
        print(f"AI Learning Layer: Updated Worker {worker_id} | New Rating: {new_rating:.2f} | New Avg Time: {new_avg_time:.2f}")

    @staticmethod
    def calculate_resolution_time(created_at_str, resolved_at_str):
        """
        Calculates time difference in minutes.
        """
        try:
            # Format: 2024-01-01 12:00:00 (SQLite default)
            fmt = '%Y-%m-%d %H:%M:%S'
            start = datetime.strptime(created_at_str, fmt)
            end = datetime.strptime(resolved_at_str, fmt)
            delta = end - start
            return max(1, int(delta.total_seconds() / 60))
        except Exception as e:
            print(f"Time Calculation Error: {e}")
            return 30 # Default fallback
