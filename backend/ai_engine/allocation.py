# --- STEP 8: Skill Matching Engine ---
# Maps complaint categories/tags to specific official skills
SKILL_MAPPING = {
    "Occupational Safety": ["Occupational Safety", "Safety", "Emergency Response", "First Aid"],
    "Mine Operations": ["Mine Operations", "Mining", "Production", "Heavy Equipment"],
    "Ventilation & Gas Monitoring": ["Ventilation", "Gas Monitoring", "Mine Safety"],
    "Electrical & Mechanical": ["Electrical", "Mechanical", "Maintenance", "Power Dept"],
    "Environmental Compliance": ["Environment", "Environmental Compliance", "Pollution Control"],
    "Labor Welfare": ["Labor Welfare", "Human Resources", "Medical", "Worker Welfare"],
    "Regulatory Compliance": ["Regulatory Compliance", "Audit", "Mine Survey", "Legal"],
    "Community & Land Relations": ["Community Relations", "Land Management", "Resettlement"],
    "Other": ["General", "Administrative"]
}

import math

# --- STEP 9: Civic Geolocation Data ---
# Mapping city areas to (lat, lon) for distance calculation
CIVIC_COORDINATES = {
    "Ward 1": (28.6139, 77.2090),
    "Ward 2": (28.6120, 77.2080),
    "Civil Lines": (28.6300, 77.2200),
    "Central Market": (28.6150, 77.2100),
    "Industrial Area": (28.6250, 77.2300),
    "Bus Stand": (28.6155, 77.2120),
    "Railway Station": (28.6160, 77.2130),
    "Airport District": (28.5562, 77.1000),
    "City Park": (28.6105, 77.2070),
}

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculates the distance (in meters) between two points using a simple Euclidean approximation 
    for small campus scales.
    """
    if None in [lat1, lon1, lat2, lon2]: return 1000 # Default to far if no GPS
    # Approx 1 degree = 111km
    dx = (lon2 - lon1) * 111000 * math.cos(math.radians(lat1))
    dy = (lat2 - lat1) * 111000
    return math.sqrt(dx*dx + dy*dy)

def allocate_task(complaint_category, complaint_location, available_workers, detected_sub_skill=None, priority="Medium"):
    """
    STEP 10: Intelligent Assignment & Emergency Override
    Score = (SkillMatch × w1) + (DistanceScore × w2) + (Performance × w3) - (Workload × w4)
    """
    best_worker = None
    max_score = -500.0 
    
    # 1. Get Complaint Coordinates
    comp_coords = CIVIC_COORDINATES.get(complaint_location, (28.6140, 77.2095))
    
    # --- STEP 10: EMERGENCY OVERRIDE ---
    # If priority is High, we maximize weight on Distance (W2) and Skill (W1), 
    # minimizing Workload penalty to ensure the absolutely nearest expert reaches quickly.
    is_emergency = (priority == "High")
    
    W1_SKILL = 1.0
    W2_DISTANCE = 3.0 if is_emergency else 0.6 # Heavy weight on distance for emergencies
    W3_PERF = 8.0
    W4_WORKLOAD = 2.0 if is_emergency else 10.0 # Reduce penalty for emergencies
    
    # Priority skill detection
    target_skill = detected_sub_skill or complaint_category
    
    for worker in available_workers:
        # Mandatory Filter: Eliminate if skill is completely unrelated
        if worker['skill'] not in SKILL_MAPPING.get(complaint_category, []) and worker['skill'] != target_skill:
            continue
            
        # Skill Match Score (W1)
        skill_score = 100 if worker['skill'] == target_skill else 50
        
        # Distance Scoring (W2)
        dist_m = calculate_distance(comp_coords[0], comp_coords[1], worker.get('latitude'), worker.get('longitude'))
        # Distance Score: Max 100 points for 0m, drops to 0 at 500m
        distance_raw = max(0, 100 * (1 - (dist_m / 500)))
        
        # Performance/Rating Score (W3)
        perf_score = worker.get('performance_rating', 5.0) # 0 to 5
        
        # Workload Penalty (W4)
        load = worker.get('load', 0)

        # 4. Historical Efficiency Score (W5 - Step 11 Learning Layer)
        W5_SPEED = 0.5
        # Lower resolution time is better. Base: 60 mins. High performance below 20 mins.
        hist_time = worker.get('avg_resolution_time', 30.0) or 30.0
        speed_score = max(0, 50 * (1 - (min(hist_time, 60) / 60)))
        
        # --- WEIGHTED FORMULA ---
        final_score = (skill_score * W1_SKILL) + \
                      (distance_raw * W2_DISTANCE) + \
                      (perf_score * W3_PERF) + \
                      (speed_score * W5_SPEED) - \
                      (load * W4_WORKLOAD)
        
        print(f"Candidate: {worker['name']} | Skill: {skill_score} | Dist: {int(dist_m)}m | Speed: {int(hist_time)}m | Load: {load} | Total: {final_score:.2f}")

        if final_score > max_score:
            max_score = final_score
            best_worker = worker
            
    return best_worker['id'] if best_worker else None
