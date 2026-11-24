import os
from datetime import datetime
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
import pymongo
import mongomock
try:
    import certifi
    CA_FILE = certifi.where()
except Exception:
    CA_FILE = None

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/bloghub")
SECRET_KEY = os.getenv("SECRET_KEY", "bloghub_cse458_web_db_2026_key")
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Global tracking for diagnostic endpoints
last_db_error = None

def get_db():
    """
    Connect to real MongoDB if available;
    Fallback gracefully to in-memory mongomock if MongoDB is offline,
    so the app runs instantly and reliably anywhere!
    """
    global last_db_error
    is_mock = False
    try:
        # Atlas cloud connection across regions (e.g. Render Oregon to Atlas Mumbai)
        # requires sufficient timeout for DNS SRV lookup and TLS handshake (15 seconds)
        timeout_ms = 15000 if ("mongodb+srv" in MONGO_URI or "@" in MONGO_URI) else 2500
        client_kwargs = {
            "serverSelectionTimeoutMS": timeout_ms
        }
        if CA_FILE and ("mongodb+srv" in MONGO_URI or "@" in MONGO_URI):
            client_kwargs["tlsCAFile"] = CA_FILE

        client = pymongo.MongoClient(MONGO_URI, **client_kwargs)
        # Trigger connection check
        client.server_info()
        db = client.get_database("bloghub")
        last_db_error = None
        print(f"[*] Successfully connected to MongoDB at: {MONGO_URI}")
    except Exception as e:
        last_db_error = str(e)
        print(f"[!] Live MongoDB not reachable ({e}). Using mongomock in-memory database fallback.")
        client = mongomock.MongoClient()
        db = client["bloghub"]
        is_mock = True

    # Setup indexes
    try:
        db.users.create_index("username", unique=True)
        db.users.create_index("email", unique=True)
        db.posts.create_index([("created_at", pymongo.DESCENDING)])
    except Exception:
        pass

    # Seed initial sample data if empty
    seed_initial_data(db)

    return db, is_mock

def seed_initial_data(db):
    """Seed initial team demo users and high quality blog posts if collection is empty"""
    if db.users.count_documents({}) == 0:
        demo_user = {
            "name": "Utsho Roy",
            "username": "utsho_roy",
            "email": "utsho@bloghub.local",
            "password": generate_password_hash("BlogHub@2026"),
            "role": "Author & CSE Student",
            "bio": "Web enthusiast & student of B.Sc. in CSE at BUBT. Passionate about Web Database Programming and modern full-stack development.",
            "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Utsho",
            "created_at": datetime.now()
        }
        user_id = db.users.insert_one(demo_user).inserted_id

        sample_posts = [
            {
                "title": "Welcome to BlogHub: Modern Web Database Programming",
                "slug": "welcome-to-bloghub",
                "summary": "Exploring modern web architectures, NoSQL databases with MongoDB, and clean Python backend engineering.",
                "content": """Welcome to **BlogHub**! This project was designed for **CSE-458: Web Database Programming** at Bangladesh University of Business & Technology (BUBT).

Our mission is to build a modern, high-performance blogging engine equipped with comprehensive front-end and back-end validation, clean UI design, and responsive document management.

### Key Highlights of BlogHub:
1. **Full-Stack Architecture:** Python (Flask) with an elegant HTML5/CSS3 modern design.
2. **MongoDB Database:** Document-oriented NoSQL storage for flexible schemas, tags, likes, and comments.
3. **Rigorous Validation:** Every input—from username patterns and password complexity to post word counts—is strictly checked on both client and server side.
4. **Interactive Features:** Real-time search, category filtering, reading time estimates, and comment threads.

Feel free to register an account, publish your own thoughts, and explore the power of modern web technologies!""",
                "category": "Web Development",
                "tags": ["Python", "MongoDB", "Flask", "WebDev"],
                "cover_image": "https://images.unsplash.com/photo-1499750310107-5fef28a66643?auto=format&fit=crop&w=1200&q=80",
                "author_id": user_id,
                "author_name": "Utsho Roy",
                "author_username": "utsho_roy",
                "views": 142,
                "likes": [],
                "comments": [
                    {
                        "author_name": "Mst. Sumaiya Akter",
                        "text": "Great initiative and beautiful design! Looking forward to sharing more technical posts here.",
                        "created_at": datetime.now()
                    }
                ],
                "created_at": datetime.now()
            },
            {
                "title": "Why MongoDB is Ideal for Modern Content Management",
                "slug": "why-mongodb-is-ideal-for-content-management",
                "summary": "Comparing traditional relational schemas with flexible BSON document stores for blogs, metadata, and dynamic content.",
                "content": """Content management platforms thrive on flexibility. A blog post often needs diverse metadata: tags, view counters, user reaction lists, dynamic comments, and rich media links.

In relational databases, storing tags and comments often requires multiple join tables (e.g., `posts_tags`, `comments`, `likes`). 

With **MongoDB**:
- **Rich Document Model:** Posts can embed comments, like user arrays, and tag lists directly or reference them cleanly.
- **Horizontal Scalability:** Handles massive reads and writes with natural sharding.
- **Speed and Simplicity:** Python's PyMongo maps directly to native Python dictionaries, minimizing ORM overhead.

BlogHub leverages these strengths to deliver lightning-fast read operations and intuitive schema design.""",
                "category": "Database",
                "tags": ["MongoDB", "NoSQL", "DatabaseDesign"],
                "cover_image": "https://images.unsplash.com/photo-1544383835-bda2bc66a55d?auto=format&fit=crop&w=1200&q=80",
                "author_id": user_id,
                "author_name": "Utsho Roy",
                "author_username": "utsho_roy",
                "views": 98,
                "likes": [],
                "comments": [],
                "created_at": datetime.now()
            }
        ]
        db.posts.insert_many(sample_posts)
