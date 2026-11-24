# BlogHub — Web-Based Blogging Platform

> **Write • Share • Explore**  
> Developed for **CSE-458: Web Database Programming**  
> **Department:** B.Sc. in Computer Science and Engineering (CSE)  
> **Institution:** Bangladesh University of Business & Technology (BUBT)

---

## 👥 Project Team Members
| No. | Student Name | Student ID |
|:---|:---|:---|
| 1 | **Mst. Sumaiya Akter** | 22235103059 |
| 2 | **Utsho Roy** | 22235103261 |
| 3 | **Afrin Akter Achol** | 22235103358 |
| 4 | **MD. Arifur Rahaman** | 21225103159 |

---

## 🛠️ Technology Stack
* **Frontend:** HTML5, Modern CSS3 (Glassmorphism, Dark Theme, Flexbox & CSS Grid, Animations), Vanilla JavaScript (ES6+).
* **Backend:** Python 3 (Flask framework, Werkzeug Security for password hashing).
* **Database:** MongoDB (using PyMongo, with automatic fallback to in-memory `mongomock` if local server is not active).

---

## ✨ Features & Architecture

1. **User Authentication & Authorization:**
   - Account Registration with full name, username, email, password, and optional author bio.
   - Secure login with session cookies.
   - Role-based permissions: only authors can edit or delete their own stories.

2. **Full CRUD Blog Management:**
   - **Create:** Publish new stories with title, category, tags, cover image URL, and markdown-friendly content.
   - **Read:** Homepage feed, trending carousel, category filtering, search by keyword, and dedicated article detail view.
   - **Update:** Edit existing stories with prefilled data and live preview.
   - **Delete:** Safe delete with confirmation modal.

3. **Community & Engagement:**
   - Real-time AJAX like button toggle.
   - Discussion / Comments thread with timestamp and author attribution.
   - Author profile page showing total published articles, cumulative view counts, and total likes received.
   - Reading time estimation (WPM algorithm) and view tracking.

---

## 🛡️ Comprehensive Validation System

BlogHub implements strict, multi-tiered validation on **both Client (Frontend)** and **Server (Backend)**:

### 1. User Registration Validation:
- **Full Name:** 2 to 60 characters, letters, spaces, hyphens, and periods only.
- **Username:** 3 to 25 characters, alphanumeric & underscore only (`^[a-z0-9_]+$`).
  - **Live AJAX Check:** Instant frontend check against `/api/validate/username` to inform the user if the username is available or already taken.
- **Email:** Strict regex format (`user@domain.com`).
  - **Live AJAX Check:** Instant check against `/api/validate/email` for duplicates.
- **Password Complexity:** Minimum 8 characters, requiring at least:
  - 1 Uppercase letter (A-Z)
  - 1 Lowercase letter (a-z)
  - 1 Numeric digit (0-9)
  - 1 Special character (`!@#$%^&*`, etc.)
  - **Dynamic Password Strength Meter:** Visual meter bar with real-time requirements checklist.
- **Confirm Password:** Real-time match verification.

### 2. Story Creation & Editing Validation:
- **Title:** 5 to 150 characters, live counter.
- **Category:** Required selection from authorized topics.
- **Content:** Minimum 30 characters, maximum 30,000 characters. Live word count and reading time estimate.
- **Cover Image:** Validated HTTP/HTTPS URL format with live image preview box.
- **Tags:** Up to 8 comma-separated tags, 2-25 characters each.

### 3. Comments Validation:
- Non-empty, minimum 2 characters, maximum 600 characters with live character counter.

---

## 🚀 How to Run the Application

### 1. Prerequisites:
Make sure Python 3.10+ is installed.

### 2. Install Dependencies:
```bash
python -m pip install -r requirements.txt
```

### 3. Configure Database (Optional):
The app runs out-of-the-box using the built-in fallback mock database.  
If you want to connect to a live MongoDB instance or MongoDB Atlas, create a `.env` file or set the environment variable:
```env
MONGO_URI=mongodb://localhost:27017/bloghub
SECRET_KEY=your_secret_key_here
PORT=5000
DEBUG=True
```

### 4. Run the Application:
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

### 5. Run Automated Tests:
```bash
python test_app.py
```
All unit and integration tests will verify the database queries, validation rules, authentication, and API endpoints.

---

## 🔑 Demo Account
For quick evaluation, sample data and an initial author account are pre-seeded:
- **Username / Email:** `utsho_roy` or `utsho@bloghub.local`
- **Password:** `BlogHub@2026`
