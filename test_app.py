import unittest
from bson import ObjectId
from app import app, db

class BlogHubTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        # Clean up test accounts to ensure predictable test runs
        db.users.delete_many({"username": {"$in": ["achol_cse", "test_user_1", "test_user_2", "brand_new_user_99"]}})
        # Reset default user name
        db.users.update_one({"username": "utsho_roy"}, {"$set": {"name": "Utsho Roy"}})
        # Reset post likes array
        db.posts.update_many({}, {"$set": {"likes": []}})

    def test_01_homepage_loads(self):
        """Test home page renders successfully with seeded posts"""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"BlogHub", res.data)
        self.assertIn(b"Welcome to BlogHub", res.data)
        self.assertIn(b"Web Database Programming", res.data)

    def test_02_registration_validation(self):
        """Test user registration validations (weak password, invalid email, success)"""
        # 1. Weak password (no special char, no uppercase)
        res_weak = self.client.post("/register", data={
            "name": "Test User",
            "username": "test_user_1",
            "email": "test1@example.com",
            "password": "simplepassword",
            "confirm_password": "simplepassword"
        }, follow_redirects=True)
        self.assertIn(b"Password must include at least one uppercase letter", res_weak.data)

        # 2. Mismatched passwords
        res_mismatch = self.client.post("/register", data={
            "name": "Test User",
            "username": "test_user_2",
            "email": "test2@example.com",
            "password": "Password123!",
            "confirm_password": "Password123Different!"
        }, follow_redirects=True)
        self.assertIn(b"Passwords do not match", res_mismatch.data)

        # 3. Successful registration
        res_success = self.client.post("/register", data={
            "name": "Afrin Akter Achol",
            "username": "achol_cse",
            "email": "achol@bubt.edu.bd",
            "password": "StrongPassword@2026",
            "confirm_password": "StrongPassword@2026",
            "bio": "CSE Student at BUBT."
        }, follow_redirects=True)
        self.assertEqual(res_success.status_code, 200)
        self.assertIn(b"Welcome to BlogHub, Afrin Akter Achol!", res_success.data)

        # 4. Logout before attempting duplicate registration
        self.client.get("/logout")

        # Duplicate username check
        res_dup = self.client.post("/register", data={
            "name": "Afrin Duplicate",
            "username": "achol_cse",
            "email": "achol2@bubt.edu.bd",
            "password": "StrongPassword@2026",
            "confirm_password": "StrongPassword@2026"
        }, follow_redirects=True)
        self.assertIn(b"This username is already taken", res_dup.data)

    def test_03_login_validation(self):
        """Test login validation with incorrect and correct credentials"""
        # Wrong password
        res_fail = self.client.post("/login", data={
            "identifier": "utsho_roy",
            "password": "WrongPassword999!"
        }, follow_redirects=True)
        self.assertIn(b"Invalid username/email or password", res_fail.data)

        # Correct password for seeded user
        res_ok = self.client.post("/login", data={
            "identifier": "utsho_roy",
            "password": "BlogHub@2026"
        }, follow_redirects=True)
        self.assertEqual(res_ok.status_code, 200)
        self.assertIn(b"Welcome back, Utsho Roy!", res_ok.data)

    def test_04_api_realtime_validation(self):
        """Test AJAX validation endpoints for username and email availability"""
        # Taken username
        res_taken_u = self.client.get("/api/validate/username?username=utsho_roy")
        self.assertEqual(res_taken_u.status_code, 200)
        self.assertFalse(res_taken_u.json["valid"])
        self.assertIn("already taken", res_taken_u.json["message"])

        # Available username
        res_avail_u = self.client.get("/api/validate/username?username=brand_new_user_99")
        self.assertEqual(res_avail_u.status_code, 200)
        self.assertTrue(res_avail_u.json["valid"])

        # Invalid email format
        res_bad_email = self.client.get("/api/validate/email?email=invalid-email-string")
        self.assertFalse(res_bad_email.json["valid"])

        # Available email
        res_avail_e = self.client.get("/api/validate/email?email=fresh@bubt.edu.bd")
        self.assertTrue(res_avail_e.json["valid"])

    def test_05_post_creation_and_view(self):
        """Test post creation requires login, enforces validation, and publishes cleanly"""
        # Login first
        self.client.post("/login", data={
            "identifier": "utsho_roy",
            "password": "BlogHub@2026"
        })

        # Post with too short title (<5 chars)
        res_short = self.client.post("/post/create", data={
            "title": "Hey",
            "category": "Web Development",
            "content": "This content is long enough to meet requirements."
        }, follow_redirects=True)
        self.assertIn(b"Title must be at least 5 characters long", res_short.data)

        # Valid post creation
        res_valid = self.client.post("/post/create", data={
            "title": "Scaling Full-Stack Web Applications with Python and MongoDB",
            "category": "Database",
            "tags": "Python, MongoDB, WebArchitecture",
            "summary": "Practical guidelines on scaling web applications from scratch.",
            "content": "This is a comprehensive article exploring query optimization, document indexing, and clean controller validation patterns in modern web systems."
        }, follow_redirects=True)
        self.assertEqual(res_valid.status_code, 200)
        self.assertIn(b"Scaling Full-Stack Web Applications", res_valid.data)

    def test_06_like_and_comment(self):
        """Test like toggle and comment submission"""
        # Login
        self.client.post("/login", data={
            "identifier": "utsho_roy",
            "password": "BlogHub@2026"
        })

        # Get existing post id
        post = db.posts.find_one({})
        post_id = str(post["_id"])

        # Like the post
        res_like = self.client.post(f"/post/{post_id}/like", headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(res_like.status_code, 200)
        self.assertTrue(res_like.json["liked"])

        # Add comment
        res_comment = self.client.post(f"/post/{post_id}/comment", data={
            "comment": "Outstanding technical architecture and clear explanations!"
        }, follow_redirects=True)
        self.assertIn(b"Your comment has been posted!", res_comment.data)

    def test_07_profile_avatar_update(self):
        """Test updating profile avatar via device file upload"""
        import io

        # 1. Login
        self.client.post("/login", data={
            "identifier": "utsho_roy",
            "password": "BlogHub@2026"
        })

        # 2. Update via File Upload
        fake_image = (io.BytesIO(b"fake-image-bytes-data-new"), "avatar_test.png")
        res_file = self.client.post("/profile/update", data={
            "name": "Utsho Roy",
            "bio": "Bio with uploaded file avatar.",
            "avatar_file": fake_image
        }, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(res_file.status_code, 200)
        self.assertIn(b"Your profile and avatar have been updated!", res_file.data)

        updated_user_file = db.users.find_one({"username": "utsho_roy"})
        self.assertTrue(
            updated_user_file["avatar"].startswith("/static/uploads/") or
            "cloudinary" in updated_user_file["avatar"]
        )

    def test_08_author_can_delete_own_post(self):
        """Test author can delete their own post and unauthorized user cannot"""
        # 1. Login as author (utsho_roy)
        self.client.post("/login", data={
            "identifier": "utsho_roy",
            "password": "BlogHub@2026"
        })

        # 2. Create a test post to delete
        res_create = self.client.post("/post/create", data={
            "title": "Post To Be Deleted By Author",
            "category": "Technology",
            "summary": "This is a temporary post that will be deleted shortly by the author.",
            "content": "Here is the full content of the post to be deleted to satisfy minlength.",
            "tags": "Test, Deletion"
        }, follow_redirects=True)
        self.assertEqual(res_create.status_code, 200)

        created_post = db.posts.find_one({"title": "Post To Be Deleted By Author"})
        self.assertIsNotNone(created_post)
        post_id = str(created_post["_id"])

        # 3. Delete post as author
        res_delete = self.client.post(f"/post/{post_id}/delete", follow_redirects=True)
        self.assertEqual(res_delete.status_code, 200)
        self.assertIn(b"permanently deleted", res_delete.data)

        # 4. Verify post no longer exists in database
        deleted_check = db.posts.find_one({"_id": ObjectId(post_id)})
        self.assertIsNone(deleted_check)

if __name__ == "__main__":
    unittest.main()
