# Enhanced Database Design - 3 Table Normalized Schema
## Smart Complaint Management System

---

## ✅ **STEP 5: DATABASE DESIGN - COMPLETE**

### **Proper Normalization with 3 Tables**

---

## 📊 **Database Schema (3rd Normal Form)**

### **Table 1: users**

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Columns:**
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO INCREMENT | Unique user identifier |
| `name` | TEXT | NOT NULL | Full name of user |
| `email` | TEXT | UNIQUE, NOT NULL | Email address (used for login) |
| `password` | TEXT | NOT NULL | Hashed password (Werkzeug) |
| `role` | TEXT | NOT NULL, DEFAULT 'user' | Role: 'user' or 'admin' |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Account creation date |

**Sample Data:**
```sql
INSERT INTO users VALUES
(1, 'Admin User', 'admin@complaint.com', 'hashed_password', 'admin', '2024-01-20 10:00:00'),
(2, 'John Doe', 'john@example.com', 'hashed_password', 'user', '2024-01-20 11:00:00'),
(3, 'Jane Smith', 'jane@example.com', 'hashed_password', 'user', '2024-01-20 12:00:00');
```

---

### **Table 2: complaints**

```sql
CREATE TABLE complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'Pending',
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

**Columns:**
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO INCREMENT | Unique complaint identifier |
| `user_id` | INTEGER | NOT NULL, FOREIGN KEY | References users(id) |
| `title` | TEXT | NOT NULL | Brief complaint summary |
| `category` | TEXT | NOT NULL | Infrastructure/Academics/Hostel/Other |
| `description` | TEXT | NOT NULL | Detailed complaint description |
| `status` | TEXT | DEFAULT 'Pending' | Pending/In Progress/Resolved |
| `date` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Submission date/time |

**Foreign Key:**
- `user_id` → `users(id)` with `ON DELETE CASCADE`
  - If user is deleted, their complaints are also deleted

**Sample Data:**
```sql
INSERT INTO complaints VALUES
(1, 2, 'Library AC not working', 'Infrastructure', 'AC broken for 2 days...', 'Pending', '2024-01-20 13:00:00'),
(2, 2, 'Assignment portal down', 'Academics', 'Cannot submit assignments...', 'In Progress', '2024-01-20 14:00:00'),
(3, 3, 'Hot water issue', 'Hostel', 'No hot water in morning...', 'Resolved', '2024-01-20 15:00:00');
```

---

### **Table 3: admin_actions** ⭐ NEW!

```sql
CREATE TABLE admin_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL,
    admin_id INTEGER NOT NULL,
    remark TEXT,
    status TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
    FOREIGN KEY (admin_id) REFERENCES users(id)
);
```

**Columns:**
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO INCREMENT | Unique action identifier |
| `complaint_id` | INTEGER | NOT NULL, FOREIGN KEY | References complaints(id) |
| `admin_id` | INTEGER | NOT NULL, FOREIGN KEY | References users(id) (admin who acted) |
| `remark` | TEXT | NULL | Admin's comment/response |
| `status` | TEXT | NULL | Status set by admin |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When action was taken |

**Foreign Keys:**
- `complaint_id` → `complaints(id)` with `ON DELETE CASCADE`
  - If complaint is deleted, all related admin actions are deleted
- `admin_id` → `users(id)`
  - Tracks which admin made the update

**Sample Data:**
```sql
INSERT INTO admin_actions VALUES
(1, 1, 1, 'We are investigating this issue.', 'In Progress', '2024-01-20 13:30:00'),
(2, 1, 1, 'AC has been repaired.', 'Resolved', '2024-01-20 14:00:00'),
(3, 2, 1, 'Portal will be fixed by evening.', 'In Progress', '2024-01-20 14:15:00'),
(4, 3, 1, 'Hot water system fixed.', 'Resolved', '2024-01-20 15:10:00');
```

---

## 🔗 **Entity-Relationship Diagram**

```
┌─────────────────┐
│     USERS       │
├─────────────────┤
│ id (PK)         │
│ name            │
│ email (UNIQUE)  │
│ password        │
│ role            │
│ created_at      │
└─────┬───────────┘
      │
      │ 1:N (One user → Many complaints)
      │
      ▼
┌─────────────────┐
│   COMPLAINTS    │
├─────────────────┤
│ id (PK)         │
│ user_id (FK) ───┼─── References users(id)
│ title           │
│ category        │
│ description     │
│ status          │
│ date            │
└─────┬───────────┘
      │
      │ 1:N (One complaint → Many admin actions)
      │
      ▼
┌───────────────────┐
│  ADMIN_ACTIONS    │
├───────────────────┤
│ id (PK)           │
│ complaint_id (FK) ┼─── References complaints(id)
│ admin_id (FK) ────┼─── References users(id)
│ remark            │
│ status            │
│ updated_at        │
└───────────────────┘
```

---

## 📐 **Normalization Analysis**

### **1st Normal Form (1NF):** ✅
- All columns contain atomic (single) values
- No repeating groups
- Each column has a unique name
- Order of rows doesn't matter

### **2nd Normal Form (2NF):** ✅
- Satisfies 1NF
- No partial dependencies
- All non-key attributes depend on the entire primary key

### **3rd Normal Form (3NF):** ✅
- Satisfies 2NF
- No transitive dependencies
- All attributes depend only on the primary key

**Example of 3NF:**
- Complaint's `status` doesn't depend on `user_id`
- Admin actions are tracked separately (not in complaints table)
- User's `role` is in users table (not duplicated)

---

## 🎯 **Advantages of This Design**

### **1. Audit Trail**
```sql
-- View all admin actions for a complaint
SELECT 
    aa.updated_at,
    u.name as admin_name,
    aa.status,
    aa.remark
FROM admin_actions aa
JOIN users u ON aa.admin_id = u.id
WHERE aa.complaint_id = 1
ORDER BY aa.updated_at DESC;
```

**Result:**
| updated_at | admin_name | status | remark |
|------------|------------|--------|--------|
| 2024-01-20 14:00:00 | Admin User | Resolved | AC has been repaired. |
| 2024-01-20 13:30:00 | Admin User | In Progress | We are investigating... |

### **2. Multiple Updates History**
- Track every status change
- See who made each update
- Know when each action occurred
- Complete timeline of complaint resolution

### **3. Better Reporting**
```sql
-- Admin activity report
SELECT 
    u.name,
    COUNT(aa.id) as actions_count,
    COUNT(DISTINCT aa.complaint_id) as complaints_handled
FROM users u
JOIN admin_actions aa ON u.id = aa.admin_id
WHERE u.role = 'admin'
GROUP BY u.id;
```

### **4. Referential Integrity**
- `ON DELETE CASCADE` ensures data consistency
- Orphaned records are automatically cleaned up
- Foreign key constraints enforce relationships

---

## 🔍 **Common Queries**

### **1. Get all complaints with latest admin action:**
```sql
SELECT 
    c.*,
    u.name as user_name,
    u.email as user_email,
    aa.remark as latest_remark,
    aa.updated_at as last_updated
FROM complaints c
JOIN users u ON c.user_id = u.id
LEFT JOIN admin_actions aa ON c.id = aa.complaint_id
WHERE aa.id = (
    SELECT MAX(id) 
    FROM admin_actions 
    WHERE complaint_id = c.id
)
ORDER BY c.date DESC;
```

### **2. Get complaint history:**
```sql
SELECT 
    c.id,
    c.title,
    aa.status,
    aa.remark,
    u.name as admin_name,
    aa.updated_at
FROM complaints c
LEFT JOIN admin_actions aa ON c.id = aa.complaint_id
LEFT JOIN users u ON aa.admin_id = u.id
WHERE c.id = ?
ORDER BY aa.updated_at ASC;
```

### **3. Admin performance:**
```sql
SELECT 
    u.name as admin_name,
    COUNT(DISTINCT aa.complaint_id) as complaints_handled,
    COUNT(CASE WHEN aa.status = 'Resolved' THEN 1 END) as resolved_count,
    AVG(julianday(aa.updated_at) - julianday(c.date)) as avg_resolution_days
FROM users u
JOIN admin_actions aa ON u.id = aa.admin_id
JOIN complaints c ON aa.complaint_id = c.id
WHERE u.role = 'admin' AND aa.status = 'Resolved'
GROUP BY u.id;
```

### **4. Complaint statistics by category:**
```sql
SELECT 
    category,
    COUNT(*) as total,
    COUNT(CASE WHEN status = 'Pending' THEN 1 END) as pending,
    COUNT(CASE WHEN status = 'In Progress' THEN 1 END) as in_progress,
    COUNT(CASE WHEN status = 'Resolved' THEN 1 END) as resolved
FROM complaints
GROUP BY category;
```

---

## 🛠️ **Migration from Old Schema**

### **Old Schema (2 tables):**
```sql
users (id, username, email, password, is_admin)
complaints (id, user_id, title, description, category, status, admin_response, created_at, updated_at)
```

### **New Schema (3 tables):**
```sql
users (id, name, email, password, role)
complaints (id, user_id, title, category, description, status, date)
admin_actions (id, complaint_id, admin_id, remark, status, updated_at)
```

### **Migration Steps:**

1. **Backup existing database:**
```bash
cp complaints.db complaints_backup.db
```

2. **Delete old database** (for fresh start):
```bash
rm complaints.db
```

3. **Restart Flask app** (creates new schema):
```bash
python3 app.py
```

4. **Or migrate data manually** (if you want to keep existing data):
```sql
-- Insert users (map username to name, is_admin to role)
INSERT INTO users_new (name, email, password, role, created_at)
SELECT username, email, password, 
       CASE WHEN is_admin = 1 THEN 'admin' ELSE 'user' END,
       created_at
FROM users_old;

-- Insert complaints (map created_at to date)
INSERT INTO complaints_new (id, user_id, title, category, description, status, date)
SELECT id, user_id, title, category, description, status, created_at
FROM complaints_old;

-- Insert admin actions (from admin_response)
INSERT INTO admin_actions (complaint_id, admin_id, remark, status, updated_at)
SELECT 
    id,
    1, -- Default admin ID
    admin_response,
    status,
    updated_at
FROM complaints_old
WHERE admin_response IS NOT NULL;
```

---

## 📝 **Database Constraints**

### **Primary Keys:**
- `users.id` - Unique identifier for each user
- `complaints.id` - Unique identifier for each complaint
- `admin_actions.id` - Unique identifier for each action

### **Foreign Keys:**
- `complaints.user_id` → `users(id)` ON DELETE CASCADE
- `admin_actions.complaint_id` → `complaints(id)` ON DELETE CASCADE
- `admin_actions.admin_id` → `users(id)`

### **Unique Constraints:**
- `users.email` - No duplicate emails

### **NOT NULL Constraints:**
- users: name, email, password, role
- complaints: user_id, title, category, description
- admin_actions: complaint_id, admin_id

### **Default Values:**
- `users.role` = 'user'
- `complaints.status` = 'Pending'
- All `created_at` / `updated_at` / `date` = CURRENT_TIMESTAMP

---

## 🔒 **Data Integrity Rules**

### **1. Cascading Deletes:**
```sql
-- If user is deleted:
DELETE FROM users WHERE id = 2;
-- → All their complaints are auto-deleted
-- → All admin actions on those complaints are auto-deleted
```

### **2. Role Validation:**
```python
# In application code
VALID_ROLES = ['user', 'admin']
if role not in VALID_ROLES:
    raise ValueError("Invalid role")
```

### **3. Status Validation:**
```python
VALID_STATUSES = ['Pending', 'In Progress', 'Resolved']
if status not in VALID_STATUSES:
    raise ValueError("Invalid status")
```

### **4. Category Validation:**
```python
VALID_CATEGORIES = ['Infrastructure', 'Academics', 'Hostel', 'Other']
if category not in VALID_CATEGORIES:
    raise ValueError("Invalid category")
```

---

## 🎯 **For Viva Questions**

### **Q: Why 3 tables instead of 2?**

**Answer:**
"We use 3 tables for better normalization:

1. **users** - Stores user information
2. **complaints** - Stores complaint details  
3. **admin_actions** - Tracks all admin updates

**Benefits:**
- **Audit trail** - We can see complete history of who updated what and when
- **Multiple updates** - Multiple admins can add remarks to same complaint
- **3rd Normal Form** - No transitive dependencies, better data integrity
- **Scalability** - Easy to add features like admin performance metrics

The old design had `admin_response` directly in complaints table, which only allowed one response. The new design allows unlimited admin actions with full history."

### **Q: Explain the foreign keys.**

**Answer:**
"We have three foreign key relationships:

1. `complaints.user_id` → `users.id`
   - Links each complaint to the user who submitted it
   - `ON DELETE CASCADE` means if user is deleted, their complaints are too

2. `admin_actions.complaint_id` → `complaints.id`
   - Links each action to a specific complaint
   - `ON DELETE CASCADE` cleans up actions if complaint is deleted

3. `admin_actions.admin_id` → `users.id`
   - Tracks which admin performed each action
   - No cascade delete (we keep action history even if admin leaves)

These ensure referential integrity - we can't have orphaned records."

### **Q: What is normalization?**

**Answer:**
"Normalization is organizing data to reduce redundancy:

**1NF** - Atomic values, no repeating groups
**2NF** - No partial dependencies  
**3NF** - No transitive dependencies

Our schema is in 3NF:
- User's name doesn't depend on complaint
- Complaint's status doesn't depend on user
- Admin actions are separate (not redundant in complaints)

This prevents update anomalies and ensures data consistency."

---

## ✅ **Schema Implementation Checklist**

- [x] Table 1: users (id, name, email, password, role)
- [x] Table 2: complaints (id, user_id, title, category, description, status, date)
- [x] Table 3: admin_actions (id, complaint_id, admin_id, remark, status, updated_at)
- [x] Foreign keys defined
- [x] ON DELETE CASCADE set
- [x] Primary keys auto-increment
- [x] Default values configured
- [x] NOT NULL constraints applied
- [x] UNIQUE constraints on email
- [x] Timestamps auto-generated

---

## 🎉 **Summary**

**Enhanced Database Design:**
- ✅ **3 Tables** (proper normalization)
- ✅ **Foreign Keys** (referential integrity)
- ✅ **3rd Normal Form** (no redundancy)
- ✅ **Audit Trail** (admin actions history)
- ✅ **Cascading Deletes** (data consistency)
- ✅ **Constraints** (data validation)
- ✅ **Indexes** (performance optimization via PKs)

**This is a production-grade database design suitable for enterprise applications!**

---

**Created:** January 20, 2026  
**Status:** ✅ Complete  
**Normalization Level:** 3NF (Third Normal Form)
