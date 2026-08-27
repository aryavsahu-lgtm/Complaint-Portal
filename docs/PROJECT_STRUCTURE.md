# Project Structure

## Overview
This document explains the complete folder structure and file organization of the Smart Complaint Management System.

```
Smart Complaint System/
│
├── app.py                          # Main Flask application Factory (Entry Point)
│   ├── Registers Blueprints
│   └── Configures App
│
├── database.py                     # Database Logic
│   ├── Connection handling
│   └── Schema initialization
│
├── utils.py                        # Utility Functions
│   ├── Login Required decorators
│   └── Admin Required decorators
│
├── auth/                           # Authentication Module
│   ├── __init__.py                # Blueprint setup
│   └── routes.py                  # Login, Register, Logout logic
│
├── complaints/                     # Complaints Module
│   ├── __init__.py                # Blueprint setup
│   └── routes.py                  # Dashboard, Submit, Update logic
│
├── static/                         # Static Assets
│   ├── css/                       # Stylesheets
│   └── images/                    # Images
│
├── templates/                      # HTML Templates (View)
│   ├── base.html                  # Base template with navbar, footer, styles
│   ├── index.html                 # Home page
│   ├── register.html              # User registration form
│   ├── login.html                 # User login form
│   ├── user_dashboard.html        # User's complaints dashboard
│   ├── submit_complaint.html      # Complaint submission form
│   └── admin_dashboard.html       # Admin management dashboard
│
├── complaints.db                   # SQLite Database (Model) - Auto-created
│   ├── users table                # Stores user accounts
│   └── complaints table           # Stores complaint records
│
├── requirements.txt                # Python dependencies
├── README.md                      # Project documentation
├── .gitignore                     # Git ignore rules
└── PROJECT_STRUCTURE.md           # This file
```

## Detailed File Descriptions

### 1. app.py (Entry Point)
**Purpose**: Serves as the application factory, registering blueprints and handling configuration.

### 2. auth/ (Authentication Blueprint)
**Purpose**: Modularizes user authentication logic.
- `routes.py`: Handles `/login`, `/register`, `/logout`.

### 3. complaints/ (Complaints Blueprint)
**Purpose**: Modularizes core business logic.
- `routes.py`: Handles `/user/dashboard`, `/submit-complaint`, `/admin/dashboard`, `/update-complaint`.

### 4. database.py
**Purpose**: Centralizes database connection and initialization logic.
- `get_db()`: Database connection helper
- `init_db()`: Database initialization function (creates tables, default admin)

---

## Data Flow

### User Registration Flow:
```
User fills form → POST to /register (auth bp) → Validate data → 
Hash password → Insert into users table → 
Redirect to login with flash message
```

### Login Flow:
```
User submits credentials → POST to /login (auth bp) → 
Query users table → Verify password hash → 
Create session → Redirect to appropriate dashboard (complaints bp)
```
