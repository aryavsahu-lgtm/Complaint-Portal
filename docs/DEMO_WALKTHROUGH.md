# Demo Walkthrough Script

Use this script to smoothly demonstrate your project during your presentation.

## 1. Introduction (1 Minute)
"Good morning/afternoon. This is the **Smart Complaint Management System**. It is a web-based application designed to streamline the process of lodging and resolving complaints within an organization."

**Key Tech Mention**:
- "Built using **Python Flask** for the backend."
- "Uses **SQLite** for the database."
- "Frontend is designed with **Bootstrap 5** for responsiveness."
- "Follows a **Modular MVC Architecture** using Flask Blueprints."

## 2. User Flow Demonstration (2 Minutes)

### Step 1: Registration
1. Click **"Get Started"** or **"Register"**.
2. Create a new user (e.g., `student1`, `student1@test.com`, `pass123`).
   - Mention: "Passwords are securely hashed before storage."

### Step 2: User Dashboard & Submission
1. Login with the new user.
2. Show the **User Dashboard** (currently empty).
3. Click **"New Complaint"**.
4. Fill out the form:
   - **Title**: "WiFi Issue in Library"
   - **Category**: "Infrastructure"
   - **Description**: "The wifi signal is very weak on the 2nd floor."
5. Click **"Submit"**.
6. Show the new complaint in the dashboard with status **"Pending"**.

## 3. Admin Flow Demonstration (2 Minutes)

### Step 3: Admin Actions
1. **Logout** from the user account.
2. Login as Admin:
   - **Username**: `admin`
   - **Password**: `admin123`
3. Show the **Admin Statistics** (Total, Pending, etc.).
4. Find the "WiFi Issue" complaint in the list.
5. Click **"Manage"**.
6. Update:
   - **Status**: "In Progress" or "Resolved"
   - **Response**: "We have notified the network team. Will be fixed by tomorrow."
7. Click **"Update"**.

### Step 4: Verification
1. Logout Admin.
2. Login back as `student1`.
3. Show that the status has changed to **"Resolved"** (Green badge) and the admin response is visible.

## 4. Code Walkthrough (Optional / QA)

If asked to show code:
- **Project Structure**: Open `PROJECT_STRUCTURE.md` or just show folders. Explain `auth` vs `complaints` folders.
- **Database**: Show `database.py` and `init_db()` function.
- **Security**: Show `auth/routes.py` and point to `generate_password_hash`.
- **Decorators**: Show `utils.py` (`@login_required`) to explain how pages are protected.

## 5. Conclusion
"This system ensures transparency, efficiency, and accountability in handling complaints. It is scalable and can be extended with features like email notifications in the future."
