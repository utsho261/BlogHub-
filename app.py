import math
import os
import re
from datetime import datetime
from functools import wraps
from bson import ObjectId
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, abort
)
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

import cloudinary
import cloudinary.uploader

from config import get_db, SECRET_KEY, PORT, DEBUG
from validators import (
    validate_registration, validate_login, validate_post,
    validate_comment, allowed_avatar_file,
    CATEGORIES
)

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Configure Local Uploads Fallback
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB max file upload size

# Configure Cloudinary CDN
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

is_cloudinary_ready = bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)
if is_cloudinary_ready:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True
    )
    print(f"[*] Cloudinary CDN active for cloud: {CLOUDINARY_CLOUD_NAME}")
else:
    print("[!] Cloudinary credentials missing in .env, falling back to local file storage.")

# Initialize MongoDB connection
db, is_mock_db = get_db()
_last_db_reconnect_attempt = 0

@app.before_request
def auto_reconnect_mongo():
    """
    If the application started in mongomock mode (e.g. during cloud server boot
    before external DNS/Atlas whitelist was ready), automatically attempt to
    reconnect to live MongoDB Atlas when traffic arrives.
    """
    global db, is_mock_db, _last_db_reconnect_attempt
    import time
    if is_mock_db and (time.time() - _last_db_reconnect_attempt > 10):
        _last_db_reconnect_attempt = time.time()
        try:
            real_db, still_mock = get_db()
            if not still_mock:
                db = real_db
                is_mock_db = False
                print("[*] Automatically promoted connection from mongomock to live MongoDB Atlas!")
        except Exception:
            pass

def upload_file_to_cloud(file, folder="bloghub", prefix="img", default_url=None):
    """
    Directly uploads file from user PC/device to Cloudinary CDN.
    Falls back to local storage if Cloudinary is not configured.
    """
    if not file or not file.filename:
        return default_url

    if not allowed_avatar_file(file.filename):
        return default_url

    # Check Cloudinary at runtime so dynamic environment variables are always loaded
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")

    if cloud_name and api_key and api_secret:
        try:
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True
            )
            file.seek(0)
            res = cloudinary.uploader.upload(
                file,
                folder=folder,
                resource_type="image"
            )
            secure_url = res.get("secure_url")
            if secure_url:
                print(f"[*] Cloudinary upload successful: {secure_url}")
                return secure_url
        except Exception as e:
            print(f"[!] Cloudinary upload error: {e}. Falling back to local storage.")

    # Local fallback
    try:
        ext = file.filename.rsplit(".", 1)[1].lower()
        safe_prefix = secure_filename(prefix).lower() or "file"
        filename = f"{safe_prefix}_{int(datetime.now().timestamp())}.{ext}"
        target_dir = os.path.join(app.config["UPLOAD_FOLDER"], folder.replace("/", "_"))
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, filename)
        file.seek(0)
        file.save(file_path)
        return f"/static/uploads/{folder.replace('/', '_')}/{filename}"
    except Exception as e:
        print(f"[!] Local save error: {e}")
        return default_url

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
    current_u = session.get("user")
    if current_u and isinstance(current_u, dict):
        try:
            fresh_u = db.users.find_one({"username": current_u.get("username")})
            if fresh_u:
                current_u = {
                    "id": str(fresh_u["_id"]),
                    "name": fresh_u.get("name", current_u.get("name")),
                    "username": fresh_u.get("username", current_u.get("username")),
                    "email": fresh_u.get("email", current_u.get("email")),
                    "avatar": fresh_u.get("avatar") or f"https://api.dicebear.com/7.x/bottts/svg?seed={fresh_u.get('username')}"
                }
                session["user"] = current_u
        except Exception:
            pass
    return {
        "categories": CATEGORIES,
        "is_mock_db": is_mock_db,
        "current_year": datetime.now().year,
        "current_user": current_u
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
            avatar_file = request.files.get("avatar_file")
            avatar_url = upload_file_to_cloud(
                avatar_file,
                folder="bloghub/avatars",
                prefix=cleaned["username"],
                default_url=f"https://api.dicebear.com/7.x/initials/svg?seed={cleaned['name']}"
            )

            new_user = {
                "name": cleaned["name"],
                "username": cleaned["username"],
                "email": cleaned["email"],
                "password": generate_password_hash(cleaned["password"]),
                "bio": cleaned["bio"],
                "avatar": avatar_url,
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
            cover_file = request.files.get("cover_image")
            cover_url = upload_file_to_cloud(
                cover_file,
                folder="bloghub/covers",
                prefix="cover",
                default_url="https://images.unsplash.com/photo-1499750310107-5fef28a66643?auto=format&fit=crop&w=1200&q=80"
            )
            new_post = {
                "title": cleaned["title"],
                "category": cleaned["category"],
                "summary": cleaned["summary"],
                "content": cleaned["content"],
                "cover_image": cover_url,
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
            cover_file = request.files.get("cover_image")
            cover_url = post.get("cover_image")
            if cover_file and cover_file.filename:
                cover_url = upload_file_to_cloud(
                    cover_file,
                    folder="bloghub/covers",
                    prefix="cover",
                    default_url=cover_url
                )

            db.posts.update_one(
                {"_id": obj_id},
                {
                    "$set": {
                        "title": cleaned["title"],
                        "category": cleaned["category"],
                        "summary": cleaned["summary"],
                        "content": cleaned["content"],
                        "cover_image": cover_url,
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
    # Verify authorship by either username or author_id
    is_author = (
        str(post.get("author_username", "")).lower() == str(user.get("username", "")).lower() or
        str(post.get("author_id", "")) == str(user.get("id", ""))
    )
    if not is_author:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"success": False, "message": "Unauthorized deletion attempt."}), 403
        flash("You do not have permission to delete this post.", "danger")
        return redirect(url_for("post_detail", post_id=post_id))

    db.posts.delete_one({"_id": obj_id})

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({"success": True, "message": "Post permanently deleted."})

    flash("Your post has been permanently deleted.", "info")
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

@app.route("/profile/update", methods=["POST"])
@login_required
def update_profile():
    current_user = session["user"]
    username = current_user["username"]

    name = request.form.get("name", "").strip()
    bio = request.form.get("bio", "").strip()

    if not name or len(name) < 2 or len(name) > 60:
        flash("Name must be between 2 and 60 characters.", "danger")
        return redirect(url_for("profile", username=username))

    if len(bio) > 300:
        flash("Bio cannot exceed 300 characters.", "danger")
        return redirect(url_for("profile", username=username))

    update_fields = {"name": name, "bio": bio}

    avatar_file = request.files.get("avatar_file")
    if avatar_file and avatar_file.filename:
        new_avatar = upload_file_to_cloud(
            avatar_file,
            folder="bloghub/avatars",
            prefix=username,
            default_url=session["user"].get("avatar")
        )
        if new_avatar:
            update_fields["avatar"] = new_avatar
            session["user"]["avatar"] = new_avatar
            session.modified = True

    session["user"]["name"] = name
    session.modified = True
    db.users.update_one({"username": username}, {"$set": update_fields})

    # Update author name/avatar across user's blog posts
    post_updates = {"author_name": name}
    if "avatar" in update_fields:
        post_updates["author_avatar"] = update_fields["avatar"]
    db.posts.update_many({"author_username": username}, {"$set": post_updates})

    flash("Your profile and avatar have been updated!", "success")
    return redirect(url_for("profile", username=username))

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

@app.route("/api/db-status")
def db_diagnostic_status():
    from config import last_db_error, MONGO_URI
    return jsonify({
        "status": "connected" if not is_mock_db else "in-memory-fallback",
        "is_mock_db": is_mock_db,
        "last_error": last_db_error,
        "mongo_uri_set": bool(MONGO_URI and not MONGO_URI.startswith("mongodb://localhost")),
        "post_count": db.posts.count_documents({})
    })

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
