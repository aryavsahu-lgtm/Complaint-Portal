# Quick Setup & Running Guide
## Smart Complaint Management System

---

## ⚡ Quick Start (3 Steps)

### Step 1: Navigate to Project Directory
```bash
cd "/Users/adarshsahu/Documents/projects/Smart Complaint System"
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```
or
```bash
pip3 install -r requirements.txt
```

### Step 3: Run the Application
```bash
python3 app.py
```

### Step 4: Open Browser
Navigate to: **http://127.0.0.1:5000**

---

## 🔑 Default Login Credentials

### Admin Account:
- **Username**: `admin`
- **Password**: `admin123`

### Test User Account (if you want to create):
- Register through the web interface, or
- **Username**: `testuser`
- **Password**: `test123`

---

## 📱 First Time Usage

### For Users:
1. Click **"Register"** in navigation
2. Fill in your details
3. Click **"Register"** button
4. Login with your credentials
5. Click **"Submit Complaint"**
6. Fill the complaint form
7. View status in **"My Dashboard"**

### For Admin:
1. Login with admin credentials
2. View all complaints in dashboard
3. Click **"Manage"** on any complaint
4. Update status and add response
5. Click **"Update Complaint"**

---

## 🛠️ Troubleshooting

### Issue: "python: command not found"
**Solution**: Use `python3` instead
```bash
python3 app.py
```

### Issue: "No module named 'flask'"
**Solution**: Install requirements
```bash
pip3 install -r requirements.txt
```

### Issue: "Address already in use"
**Solution**: Port 5000 is busy. Kill the process:
```bash
lsof -ti:5000 | xargs kill -9
```
Then run the app again.

### Issue: "Database is locked"
**Solution**: 
1. Close the application (Ctrl+C)
2. Delete `complaints.db` if it exists
3. Run the application again (database will be recreated)

### Issue: Can't see admin dashboard
**Solution**: 
1. Logout from current session
2. Login with admin credentials (username: admin, password: admin123)

---

## 📂 Project Files Checklist

Make sure these files exist:
- [x] `app.py` - Main application
- [x] `requirements.txt` - Dependencies
- [x] `README.md` - Documentation
- [x] `VIVA_GUIDE.md` - Viva preparation
- [x] `PROJECT_STRUCTURE.md` - Architecture details
- [x] `templates/base.html`
- [x] `templates/index.html`
- [x] `templates/login.html`
- [x] `templates/register.html`
- [x] `templates/user_dashboard.html`
- [x] `templates/submit_complaint.html`
- [x] `templates/admin_dashboard.html`
- [x] `complaints.db` (Auto-created)

---

## 🧪 Testing the Application

### Test 1: User Registration
1. Go to http://127.0.0.1:5000
2. Click "Register"
3. Username: `demo`
4. Email: `demo@test.com`
5. Password: `demo123`
6. Confirm Password: `demo123`
7. Submit → Should redirect to login with success message

### Test 2: User Login
1. Click "Login"
2. Username: `demo`
3. Password: `demo123`
4. Submit → Should go to user dashboard

### Test 3: Submit Complaint
1. After login, click "Submit Complaint"
2. Title: `Test Complaint`
3. Category: `Technical`
4. Description: `This is a test complaint`
5. Submit → Should see in "My Dashboard"

### Test 4: Admin Management
1. Logout
2. Login as admin (username: `admin`, password: `admin123`)
3. Should see admin dashboard with statistics
4. Click "Manage" on the complaint
5. Status: `In Progress`
6. Response: `We are working on it`
7. Update → Status should change

### Test 5: View Admin Response
1. Logout
2. Login as `demo` again
3. Check dashboard
4. Click "View" on complaint
5. Should see admin response

---

## 🚀 For Presentation/Demo

### Before Demo:
1. ✅ Test the application thoroughly
2. ✅ Prepare 1-2 dummy user accounts
3. ✅ Have 2-3 sample complaints ready
4. ✅ Test on the presentation laptop
5. ✅ Ensure Flask is running
6. ✅ Open browser tab beforehand
7. ✅ Close unnecessary applications
8. ✅ Check internet connection (for Bootstrap CDN)

### Demo Flow (5-7 minutes):
1. **Introduction** (30 sec)
   - Project name and purpose
   - Technologies used

2. **Homepage Tour** (30 sec)
   - Show features
   - Explain user types

3. **User Registration** (45 sec)
   - Register new user
   - Show validation

4. **User Workflow** (1.5 min)
   - Login
   - Submit complaint
   - View dashboard

5. **Admin Workflow** (2 min)
   - Login as admin
   - Show statistics
   - Manage complaint
   - Update status and response

6. **Verification** (1 min)
   - Logout admin
   - Login as user
   - Show updated status

7. **Code Walkthrough** (1-2 min)
   - Show app.py structure
   - Explain one route
   - Show template inheritance

8. **Q&A** (Remaining time)

---

## 💾 Backup Instructions

### Create Backup:
```bash
# Backup database
cp complaints.db complaints_backup.db

# Backup entire project
cd ..
zip -r "Smart Complaint System Backup.zip" "Smart Complaint System"
```

### Restore from Backup:
```bash
# Restore database
cp complaints_backup.db complaints.db
```

---

## 🔒 Security Checklist

For Production Deployment:
- [ ] Change `app.secret_key` to a strong random value
- [ ] Set `debug=False` in app.py
- [ ] Use environment variables for sensitive data
- [ ] Add CSRF protection
- [ ] Implement rate limiting
- [ ] Use HTTPS/SSL
- [ ] Add input validation on all forms
- [ ] Set up proper error logging
- [ ] Use a production database (PostgreSQL)
- [ ] Configure a production WSGI server (Gunicorn)

---

## 📊 Database Management

### View Database:
You can use any SQLite browser:
- **DB Browser for SQLite** (Free, GUI) - Recommended
- **SQLite Studio** (Free, GUI)
- Command line:
```bash
sqlite3 complaints.db
.tables
SELECT * FROM users;
SELECT * FROM complaints;
.quit
```

### Reset Database:
```bash
# Stop the application (Ctrl+C)
rm complaints.db
python3 app.py
# Database will be recreated with default admin
```

---

## 🎯 Key Features to Highlight

During presentation, emphasize:
1. ✅ **Secure Authentication** - Password hashing
2. ✅ **Role-based Access** - User vs Admin
3. ✅ **Real-time Updates** - Status tracking
4. ✅ **Responsive Design** - Works on all devices
5. ✅ **Clean Architecture** - MVC pattern
6. ✅ **User-friendly UI** - Bootstrap components
7. ✅ **Data Integrity** - Foreign key relationships
8. ✅ **Easy Deployment** - Simple setup process

---

## 📝 Important Commands Reference

```bash
# Install Flask
pip3 install Flask

# Install specific version
pip3 install Flask==3.0.0

# List installed packages
pip3 list

# Check Flask version
python3 -c "import flask; print(flask.__version__)"

# Run with specific host and port
python3 app.py --host=0.0.0.0 --port=8080

# Run in background (macOS/Linux)
nohup python3 app.py &

# Kill Flask process
pkill -f "python3 app.py"
```

---

## 🌐 Browser Compatibility

Tested and working on:
- ✅ Chrome (Recommended)
- ✅ Firefox
- ✅ Safari
- ✅ Edge
- ✅ Mobile browsers (Chrome/Safari)

**Note**: Bootstrap 5 requires modern browsers. IE11 not supported.

---

## 📱 Responsive Breakpoints

The UI adapts at these screen sizes:
- **Desktop**: > 992px (Full layout)
- **Tablet**: 768px - 991px (Medium layout)
- **Mobile**: < 768px (Stacked layout)

Test responsive design:
1. Open browser DevTools (F12)
2. Click device toolbar icon
3. Select different devices
4. Test all pages

---

## ⚙️ Environment Setup (First Time)

### macOS Setup:
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3
brew install python3

# Verify installation
python3 --version
pip3 --version

# Navigate to project
cd "/Users/adarshsahu/Documents/projects/Smart Complaint System"

# Install requirements
pip3 install -r requirements.txt

# Run app
python3 app.py
```

### Windows Setup:
```bash
# Download Python from python.org
# Install Python (check "Add to PATH")

# Open Command Prompt
cd "C:\path\to\Smart Complaint System"

# Install requirements
pip install -r requirements.txt

# Run app
python app.py
```

### Linux Setup:
```bash
# Update package list
sudo apt update

# Install Python 3 and pip
sudo apt install python3 python3-pip

# Navigate to project
cd "/path/to/Smart Complaint System"

# Install requirements
pip3 install -r requirements.txt

# Run app
python3 app.py
```

---

## 🎓 For Examiners

### Project Highlights:
- **Complete CRUD Operations**: Create users/complaints, Read dashboards, Update status, Delete (logout)
- **Authentication & Authorization**: Secure login, role-based access
- **Database Design**: Normalized schema, foreign keys, timestamps
- **Security**: Password hashing, SQL injection protection, session management
- **UI/UX**: Modern, responsive, intuitive design
- **Code Quality**: Clean structure, comments, reusable templates
- **Documentation**: Comprehensive README, viva guide, structure documentation

### Technologies Demonstrated:
1. **Backend**: Python, Flask, SQLite
2. **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
3. **Templating**: Jinja2
4. **Security**: Werkzeug, Flask sessions
5. **Design Pattern**: MVC
6. **Version Control**: Git (optional)

---

## 📞 Support & Resources

### Official Documentation:
- Flask: https://flask.palletsprojects.com/
- Bootstrap: https://getbootstrap.com/
- SQLite: https://www.sqlite.org/
- Jinja2: https://jinja.palletsprojects.com/

### Helpful Tutorials:
- Flask Mega-Tutorial: https://blog.miguelgrinberg.com/
- W3Schools Flask: https://www.w3schools.com/python/python_flask.asp

---

## ✅ Pre-Viva Checklist

One day before:
- [ ] Test the application on presentation laptop
- [ ] Prepare backup of database with sample data
- [ ] Review VIVA_GUIDE.md thoroughly
- [ ] Practice demo 2-3 times (aim for <7 minutes)
- [ ] Prepare answers for "Why this technology?" questions
- [ ] Understand every line of code in app.py
- [ ] Test all features (registration, login, submit, update)
- [ ] Check responsive design
- [ ] Have backup plan (screenshots/video) if live demo fails

Day of viva:
- [ ] Charge laptop fully
- [ ] Test internet connection
- [ ] Open application beforehand
- [ ] Have backup user accounts ready
- [ ] Keep README.md open for reference
- [ ] Stay calm and confident

---

## 🎉 Success Criteria

Your project is successful if:
✅ Application runs without errors
✅ All features work as expected
✅ UI is responsive and professional
✅ Code is clean and well-organized
✅ Security measures are implemented
✅ Documentation is comprehensive
✅ You can explain all concepts clearly

---

**You're all set! Good luck with your presentation! 🚀**

For any queries, refer to:
- `README.md` - General documentation
- `VIVA_GUIDE.md` - Q&A preparation
- `PROJECT_STRUCTURE.md` - Technical architecture
