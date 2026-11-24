import math
import re
from datetime import datetime
from functools import wraps
from bson import ObjectId
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, abort
)
from werkzeug.security import generate_password_hash

from config import get_db, SECRET_KEY, PORT, DEBUG
from validators import (
    validate_registration, validate_login, validate_post,
    validate_comment, CATEGORIES
)

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Initialize MongoDB connection
db, is_mock_db = get_db()

# --- Custom Template Filters & Helpers ---
@app.template_filter("time_ago")
def time_ago(dt):
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    now = datetime.now()
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return "Just now"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m ago"
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours}h ago"
    days = int(hours // 24)
    if days < 30:
        return f"{days}d ago"
    return dt.strftime("%b %d, %Y")

@app.template_filter("reading_time")
def reading_time(content):
    if not content:
        return "1 min read"
    word_count = len(re.findall(r"\w+", content))
    minutes = max(1, math.ceil(word_count / 200))
    return f"{minutes} min read"

@app.context_processor
def inject_global_data():
    return {
        "categories": CATEGORIES,
        "is_mock_db": is_mock_db,
        "current_year": datetime.now().year,
        "current_user": session.get("user")
    }

# --- Authentication Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user"):
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route("/")
def index():
    query_param = request.args.get("q", "").strip()
    category_param = request.args.get("cat", "").strip()

    filter_dict = {}
    if category_param and category_param in CATEGORIES:
        filter_dict["category"] = category_param

    if query_param:
        regex_pattern = re.compile(re.escape(query_param), re.IGNORECASE)
        filter_dict["$or"] = [
            {"title": {"$regex": regex_pattern}},
            {"content": {"$regex": regex_pattern}},
            {"author_name": {"$regex": regex_pattern}},
            {"tags": {"$in": [query_param]}}
        ]

    # Fetch posts
    posts_cursor = db.posts.find(filter_dict).sort("created_at", -1)
    posts = list(posts_cursor)

    # Convert ObjectId to string for templates
    for p in posts:
        p["_id"] = str(p["_id"])
        p["likes_count"] = len(p.get("likes", []))
        p["comments_count"] = len(p.get("comments", []))

    # Stats for homepage badge counters
    total_posts = db.posts.count_documents({})
    total_authors = db.users.count_documents({})

    # Trending / popular posts (sorted by views + likes count)
    trending_posts = list(db.posts.find({}).sort("views", -1).limit(4))
    for tp in trending_posts:
        tp["_id"] = str(tp["_id"])
        tp["likes_count"] = len(tp.get("likes", []))

    return render_template(
        "index.html",
        posts=posts,
        total_posts=total_posts,
        total_authors=total_authors,
        trending_posts=trending_posts,
        search_query=query_param,
        selected_category=category_param
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user"):
        return redirect(url_for("index"))

    errors = {}
    form_data = {}

    if request.method == "POST":
        form_data = request.form.to_dict()
        is_valid, errors, cleaned = validate_registration(form_data, db)

        if is_valid:
            new_user = {
                "name": cleaned["name"],
                "username": cleaned["username"],
                "email": cleaned["email"],
                "password": generate_password_hash(cleaned["password"]),
                "bio": cleaned["bio"],
                "avatar": f"https://api.dicebear.com/7.x/initials/svg?seed={cleaned['name']}",
                "role": "Writer",
                "created_at": datetime.now()
            }
            inserted = db.users.insert_one(new_user)

            # Log user in
            session["user"] = {
                "id": str(inserted.inserted_id),
                "name": new_user["name"],
                "username": new_user["username"],
                "email": new_user["email"],
                "avatar": new_user["avatar"]
            }
            flash(f"Welcome to BlogHub, {new_user['name']}! Your account has been created.", "success")
            return redirect(url_for("index"))
        else:
            flash("Please fix the validation errors below.", "danger")

    return render_template("register.html", errors=errors, form_data=form_data)

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("index"))

    errors = {}
    form_data = {}
    next_url = request.args.get("next") or request.form.get("next") or url_for("index")

    if request.method == "POST":
        form_data = request.form.to_dict()
        user, errors = validate_login(form_data, db)

        if user:
            session["user"] = {
                "id": str(user["_id"]),
                "name": user["name"],
                "username": user["username"],
                "email": user["email"],
                "avatar": user.get("avatar", f"https://api.dicebear.com/7.x/initials/svg?seed={user['name']}")
            }
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(next_url)
        else:
            flash("Invalid credentials. Please verify your details.", "danger")

    return render_template("login.html", errors=errors, form_data=form_data, next=next_url)

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("index"))

@app.route("/post/<post_id>")
def post_detail(post_id):
    try:
        obj_id = ObjectId(post_id)
    except Exception:
        abort(404)

    # Increment view counter
    db.posts.update_one({"_id": obj_id}, {"$inc": {"views": 1}})
    post = db.posts.find_one({"_id": obj_id})
    if not post:
        abort(404)

    post["_id"] = str(post["_id"])
    likes = post.get("likes", [])
    post["likes_count"] = len(likes)
    
    current_user = session.get("user")
    post["user_has_liked"] = current_user and (current_user["id"] in likes)

    # Fetch author details for author card
    author = db.users.find_one({"username": post.get("author_username")})

    # Related posts in same category
    related_posts = list(
        db.posts.find({"category": post["category"], "_id": {"$ne": obj_id}})
        .limit(3)
    )
    for rp in related_posts:
        rp["_id"] = str(rp["_id"])

    return render_template(
        "post_detail.html",
        post=post,
        author=author,
        related_posts=related_posts
    )

@app.route("/post/create", methods=["GET", "POST"])
@login_required
def create_post():
    errors = {}
    form_data = {}

    if request.method == "POST":
        form_data = request.form.to_dict()
        is_valid, errors, cleaned = validate_post(form_data)

        if is_valid:
            user = session["user"]
            new_post = {
                "title": cleaned["title"],
                "category": cleaned["category"],
                "summary": cleaned["summary"],
                "content": cleaned["content"],
                "cover_image": cleaned["cover_image"],
                "tags": cleaned["tags"],
                "author_id": ObjectId(user["id"]) if ObjectId.is_valid(user["id"]) else user["id"],
                "author_name": user["name"],
                "author_username": user["username"],
                "views": 0,
                "likes": [],
                "comments": [],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            result = db.posts.insert_one(new_post)
            flash("Your story was published successfully!", "success")
            return redirect(url_for("post_detail", post_id=str(result.inserted_id)))
        else:
            flash("Please fix the validation errors before publishing.", "danger")

    return render_template("create_post.html", errors=errors, form_data=form_data)

@app.route("/post/<post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    try:
        obj_id = ObjectId(post_id)
    except Exception:
        abort(404)

    post = db.posts.find_one({"_id": obj_id})
    if not post:
        abort(404)

    # Check ownership
    user = session["user"]
    if str(post.get("author_username")) != user["username"]:
        flash("You are not authorized to edit this post.", "danger")
        return redirect(url_for("post_detail", post_id=post_id))

    errors = {}
    form_data = {
        "title": post["title"],
        "category": post["category"],
        "summary": post["summary"],
        "content": post["content"],
        "cover_image": post.get("cover_image", ""),
        "tags": ", ".join(post.get("tags", []))
    }

    if request.method == "POST":
        form_data = request.form.to_dict()
        is_valid, errors, cleaned = validate_post(form_data)

        if is_valid:
            db.posts.update_one(
                {"_id": obj_id},
                {
                    "$set": {
                        "title": cleaned["title"],
                        "category": cleaned["category"],
                        "summary": cleaned["summary"],
                        "content": cleaned["content"],
                        "cover_image": cleaned["cover_image"],
                        "tags": cleaned["tags"],
                        "updated_at": datetime.now()
                    }
                }
            )
            flash("Your post has been updated!", "success")
            return redirect(url_for("post_detail", post_id=post_id))
        else:
            flash("Please resolve the validation errors.", "danger")

    return render_template("edit_post.html", errors=errors, form_data=form_data, post_id=post_id)

@app.route("/post/<post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    try:
        obj_id = ObjectId(post_id)
    except Exception:
        abort(404)

    post = db.posts.find_one({"_id": obj_id})
    if not post:
        abort(404)

    user = session["user"]
    if str(post.get("author_username")) != user["username"]:
        flash("Unauthorized deletion attempt.", "danger")
        return redirect(url_for("post_detail", post_id=post_id))

    db.posts.delete_one({"_id": obj_id})
    flash("Post has been permanently deleted.", "info")
    return redirect(url_for("profile", username=user["username"]))

@app.route("/post/<post_id>/like", methods=["POST"])
@login_required
def toggle_like(post_id):
    try:
        obj_id = ObjectId(post_id)
    except Exception:
        return jsonify({"error": "Invalid Post ID"}), 400

    post = db.posts.find_one({"_id": obj_id})
    if not post:
        return jsonify({"error": "Post not found"}), 404

    user_id = session["user"]["id"]
    likes = post.get("likes", [])

    if user_id in likes:
        # Unlike
        db.posts.update_one({"_id": obj_id}, {"$pull": {"likes": user_id}})
        liked = False
        new_count = len(likes) - 1
    else:
        # Like
        db.posts.update_one({"_id": obj_id}, {"$addToSet": {"likes": user_id}})
        liked = True
        new_count = len(likes) + 1

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({"liked": liked, "likes_count": new_count})

    return redirect(url_for("post_detail", post_id=post_id))

@app.route("/post/<post_id>/comment", methods=["POST"])
@login_required
def add_comment(post_id):
    try:
        obj_id = ObjectId(post_id)
    except Exception:
        abort(404)

    is_valid, errors, comment_text = validate_comment(request.form)
    if is_valid:
        user = session["user"]
        comment_doc = {
            "comment_id": str(ObjectId()),
            "author_id": user["id"],
            "author_name": user["name"],
            "author_username": user["username"],
            "author_avatar": user.get("avatar", ""),
            "text": comment_text,
            "created_at": datetime.now()
        }
        db.posts.update_one({"_id": obj_id}, {"$push": {"comments": comment_doc}})
        flash("Your comment has been posted!", "success")
    else:
        for _, err in errors.items():
            flash(err, "danger")

    return redirect(url_for("post_detail", post_id=post_id) + "#comments")

@app.route("/profile/<username>")
def profile(username):
    user_doc = db.users.find_one({"username": username.lower()})
    if not user_doc:
        abort(404)

    user_posts = list(db.posts.find({"author_username": username.lower()}).sort("created_at", -1))
    for p in user_posts:
        p["_id"] = str(p["_id"])
        p["likes_count"] = len(p.get("likes", []))
        p["comments_count"] = len(p.get("comments", []))

    total_views = sum(p.get("views", 0) for p in user_posts)
    total_likes = sum(len(p.get("likes", [])) for p in user_posts)

    return render_template(
        "profile.html",
        profile_user=user_doc,
        posts=user_posts,
        total_views=total_views,
        total_likes=total_likes
    )

# --- Real-Time Validation API Endpoints ---
@app.route("/api/validate/username")
def check_username():
    username = request.args.get("username", "").strip().lower()
    if not username:
        return jsonify({"valid": False, "message": "Username is required."})
    if len(username) < 3 or len(username) > 25:
        return jsonify({"valid": False, "message": "Must be between 3 and 25 characters."})
    if not re.match(r"^[a-z0-9_]+$", username):
        return jsonify({"valid": False, "message": "Only letters, numbers, and underscores allowed."})

    existing = db.users.find_one({"username": username})
    if existing:
        return jsonify({"valid": False, "message": "This username is already taken."})
    return jsonify({"valid": True, "message": "Username is available!"})

@app.route("/api/validate/email")
def check_email():
    email = request.args.get("email", "").strip().lower()
    if not email:
        return jsonify({"valid": False, "message": "Email is required."})
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(email_regex, email):
        return jsonify({"valid": False, "message": "Invalid email address format."})

    existing = db.users.find_one({"email": email})
    if existing:
        return jsonify({"valid": False, "message": "Email is already registered."})
    return jsonify({"valid": True, "message": "Email is valid & available!"})

# --- Error Handlers ---
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("404.html", message="Internal Server Error occurred. Please try again."), 500

if __name__ == "__main__":
    print(f"🚀 BlogHub application starting on http://127.0.0.1:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
