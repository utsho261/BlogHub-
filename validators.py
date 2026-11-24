import re
from urllib.parse import urlparse

# Allowed Categories
CATEGORIES = [
    "Web Development",
    "Programming",
    "Technology",
    "AI & Machine Learning",
    "Database",
    "Career & Lifestyle"
]

def sanitize_text(text):
    """Strip leading/trailing whitespace and normalize spaces"""
    if not text:
        return ""
    return str(text).strip()

def validate_registration(data, db):
    """
    Comprehensive validation for user registration.
    Checks name, username format/uniqueness, email format/uniqueness, password complexity, and confirmation.
    """
    errors = {}
    name = sanitize_text(data.get("name", ""))
    username = sanitize_text(data.get("username", "")).lower()
    email = sanitize_text(data.get("email", "")).lower()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")
    bio = sanitize_text(data.get("bio", ""))

    # 1. Full Name Validation
    if not name:
        errors["name"] = "Full name is required."
    elif len(name) < 2 or len(name) > 60:
        errors["name"] = "Full name must be between 2 and 60 characters."
    elif not re.match(r"^[a-zA-Z\s\.\-']+$", name):
        errors["name"] = "Name can only contain letters, spaces, hyphens, and periods."

    # 2. Username Validation
    if not username:
        errors["username"] = "Username is required."
    elif len(username) < 3 or len(username) > 25:
        errors["username"] = "Username must be between 3 and 25 characters."
    elif not re.match(r"^[a-z0-9_]+$", username):
        errors["username"] = "Username can only contain lowercase letters, numbers, and underscores."
    else:
        # Check uniqueness in MongoDB
        if db.users.find_one({"username": username}):
            errors["username"] = "This username is already taken. Please choose another."

    # 3. Email Validation
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not email:
        errors["email"] = "Email address is required."
    elif len(email) > 100:
        errors["email"] = "Email address cannot exceed 100 characters."
    elif not re.match(email_regex, email):
        errors["email"] = "Please provide a valid email address (e.g., user@example.com)."
    else:
        # Check uniqueness in MongoDB
        if db.users.find_one({"email": email}):
            errors["email"] = "An account with this email already exists."

    # 4. Password Complexity Validation
    if not password:
        errors["password"] = "Password is required."
    elif len(password) < 8:
        errors["password"] = "Password must be at least 8 characters long."
    elif len(password) > 128:
        errors["password"] = "Password cannot exceed 128 characters."
    else:
        has_upper = re.search(r"[A-Z]", password)
        has_lower = re.search(r"[a-z]", password)
        has_digit = re.search(r"[0-9]", password)
        has_special = re.search(r"[!@#$%^&*(),.?\":{}|<>\-_]", password)

        if not (has_upper and has_lower and has_digit and has_special):
            errors["password"] = "Password must include at least one uppercase letter, one lowercase letter, one number, and one special character (!@#$%^&* etc.)."

    # 5. Confirm Password Validation
    if not confirm_password:
        errors["confirm_password"] = "Please confirm your password."
    elif password != confirm_password:
        errors["confirm_password"] = "Passwords do not match."

    # 6. Bio length
    if len(bio) > 300:
        errors["bio"] = "Bio cannot exceed 300 characters."

    cleaned = {
        "name": name,
        "username": username,
        "email": email,
        "password": password,
        "bio": bio or "Passionate writer and reader on BlogHub."
    }

    return (len(errors) == 0, errors, cleaned)

def validate_login(data, db):
    """
    Validates login credentials against MongoDB.
    Accepts either username or email.
    """
    errors = {}
    identifier = sanitize_text(data.get("identifier", "")).lower()
    password = data.get("password", "")

    if not identifier:
        errors["identifier"] = "Username or Email is required."
    if not password:
        errors["password"] = "Password is required."

    if errors:
        return None, errors

    # Find user by username or email
    user = db.users.find_one({
        "$or": [{"username": identifier}, {"email": identifier}]
    })

    if not user:
        errors["auth"] = "Invalid username/email or password."
        return None, errors

    from werkzeug.security import check_password_hash
    if not check_password_hash(user["password"], password):
        errors["auth"] = "Invalid username/email or password."
        return None, errors

    return user, errors

def validate_post(data):
    """
    Validates blog post creation and updates.
    """
    errors = {}
    title = sanitize_text(data.get("title", ""))
    category = sanitize_text(data.get("category", ""))
    summary = sanitize_text(data.get("summary", ""))
    content = sanitize_text(data.get("content", ""))
    cover_image = sanitize_text(data.get("cover_image", ""))
    tags_raw = sanitize_text(data.get("tags", ""))

    # 1. Title
    if not title:
        errors["title"] = "Blog title is required."
    elif len(title) < 5:
        errors["title"] = "Title must be at least 5 characters long."
    elif len(title) > 150:
        errors["title"] = "Title cannot exceed 150 characters."

    # 2. Category
    if not category:
        errors["category"] = "Please select a category."
    elif category not in CATEGORIES:
        errors["category"] = f"Invalid category. Must be one of: {', '.join(CATEGORIES)}"

    # 3. Content
    if not content:
        errors["content"] = "Post content cannot be empty."
    elif len(content) < 30:
        errors["content"] = "Content must be at least 30 characters long to provide value to readers."
    elif len(content) > 30000:
        errors["content"] = "Content exceeds maximum length of 30,000 characters."

    # 4. Summary (Auto-generate if missing)
    if not summary:
        # Take first 150 chars of content
        summary = content[:140].replace("\n", " ").strip() + "..."
    elif len(summary) > 300:
        errors["summary"] = "Summary cannot exceed 300 characters."

    # 5. Cover Image URL
    if cover_image:
        try:
            parsed = urlparse(cover_image)
            if not (parsed.scheme in ["http", "https"] and parsed.netloc):
                errors["cover_image"] = "Cover image must be a valid HTTP or HTTPS URL."
        except Exception:
            errors["cover_image"] = "Invalid image URL format."
    else:
        # Default high-quality placeholder cover
        cover_image = "https://images.unsplash.com/photo-1499750310107-5fef28a66643?auto=format&fit=crop&w=1200&q=80"

    # 6. Tags (comma separated)
    tag_list = []
    if tags_raw:
        raw_tags = [t.strip().replace("#", "") for t in tags_raw.split(",") if t.strip()]
        if len(raw_tags) > 8:
            errors["tags"] = "Maximum 8 tags allowed per post."
        else:
            for t in raw_tags:
                if len(t) < 2 or len(t) > 25:
                    errors["tags"] = f"Tag '{t}' must be between 2 and 25 characters."
                    break
                tag_list.append(t)
    if not tag_list:
        tag_list = [category]

    cleaned = {
        "title": title,
        "category": category,
        "summary": summary,
        "content": content,
        "cover_image": cover_image,
        "tags": tag_list
    }

    return (len(errors) == 0, errors, cleaned)

def validate_comment(data):
    """Validates user comments on posts"""
    errors = {}
    content = sanitize_text(data.get("comment", ""))

    if not content:
        errors["comment"] = "Comment text cannot be empty."
    elif len(content) < 2:
        errors["comment"] = "Comment is too short (minimum 2 characters)."
    elif len(content) > 600:
        errors["comment"] = "Comment cannot exceed 600 characters."

    return (len(errors) == 0, errors, content)
