# Advanced Smart Complaint Management System
## Project Architecture & Foundation

This document defines the architectural blueprint for the **Advanced Smart Complaint Management System**. This system builds upon the existing foundation to introduce modular, intelligent decision-making capabilities suitable for a major capstone project.

### 1. System Overview
The system is designed as a **Modular Monolith** using **Python (Flask)**. It separates concerns into clear layers:
- **Presentation Layer**: HTML/Bootstrap/JS (Voice Interface).
- **Application Layer**: Flask Routes (`auth`, `complaints`).
- **Intelligence Layer**: `ai_engine` (New modular AI components).
- **Data Layer**: SQLite (Robust relational storage).

### 2. Advanced AI Modules

#### Module A: Emotion-Aware Escalation Engine 🧠
**Purpose**: To move beyond simple keyword matching and understand the *severity* of a complaint based on the user's emotional state.
- **Logic**: 
    - Analyzes text for sentiment polarity (Positive vs. Negative) and subjectivity.
    - **Escalation Rules**:
        - `Negative Sentiment` + `Urgency Keywords` = **Critical Priority** 🚨.
        - `Neutral Sentiment` + `Urgency Keywords` = **High Priority** 🔴.
        - `Negative Sentiment` + `No Keywords` = **Medium Priority** 🟠 (Customer Service Issue).
- **Implementation**: Uses `TextBlob` or `VADER` for sentiment scoring.

#### Module B: AI-Optimized Workforce Allocation 👷
**Purpose**: To move beyond static department assignment and dynamically allocate complaints to the *best available* specific worker.
- **Logic**: Uses a weighted scoring algorithm to rank workers:
    - `Skill Score` (30%): Does the worker specialize in this (e.g., Electrician vs. Plumber)?
    - `Load Score` (40%): How many active jobs do they have? (Load Balancing).
    - `Proximity Score` (30%): Are they assigned to this location (e.g., Hostel Block A)?
- **Implementation**: A Heuristic Optimization Algorithm in Python.

### 3. Data Structure Enhancements
To support these features, the database will be enhanced:
- **Table `workers`**: `id`, `name`, `skill_set` (Electrical, Plumbing), `current_load`, `location_zone`.
- **Table `complaints`**: Added `sentiment_score` and `worker_id` (Foreign Key).

### 4. Project Structure (Updated)
```
/Smart Complaint System
├── app.py                # Entry Point
├── database.py           # Data Access Object
├── /ai_engine            # [NEW] Intelligence Layer
│   ├── __init__.py       # Package Init
│   ├── emotion.py        # Emotion Analysis Logic
│   └── allocation.py     # Workforce Optimization Logic
├── /complaints           # Complaint Management Blueprint
├── /auth                 # Authentication Blueprint
└── /templates            # Frontend Views
```

---
**Status**: Architecture Defined. Ready for Implementation. 🚀
