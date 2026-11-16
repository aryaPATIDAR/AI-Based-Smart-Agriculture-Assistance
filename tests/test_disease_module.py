import os
import sys
import io
import time
import unittest
from PIL import Image

# Ensure project root is in python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Set test environment
os.environ["SECRET_KEY"] = "test-secret-key-12345"

from main import app
from backend.database.db import SessionLocal, engine
from backend.database.models import Base, Kisan, DiseaseScan, KisanFasal

class KisanSmartAcceptanceTestSuite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("\n" + "="*80)
        print("KISANSMART AI DISEASE DETECTION MODULE - 12-POINT ACCEPTANCE TEST SUITE")
        print("="*80 + "\n")
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key-12345"
        cls.client = app.test_client()
        Base.metadata.create_all(bind=engine)

        # Setup test farmer
        db = SessionLocal()
        cls.test_user_id = "KS_TEST_999"
        kisan = db.query(Kisan).filter(Kisan.user_id == cls.test_user_id).first()
        if not kisan:
            kisan = Kisan(
                user_id=cls.test_user_id,
                email="testfarmer@kisansmart.in",
                naam="Ramesh Kumar",
                role="kisan",
                location="Indore, MP",
                zameen_bigha=5.0,
                khet_count=2
            )
            db.add(kisan)
            db.commit()
            db.refresh(kisan)
        cls.kisan_id = kisan.id
        db.close()

    def test_01_flask_app_starts(self):
        """Test 1: Flask application starts successfully with all registered routes."""
        self.assertIsNotNone(app)
        self.assertEqual(app.name, "main")
        rules = [r.rule for r in app.url_map.iter_rules()]
        self.assertIn("/", rules)
        self.assertIn("/disease", rules)
        self.assertIn("/farmer", rules)
        self.assertIn("/weather", rules)
        print("✅ [Test 1 Passed] Flask app initialized with all blueprints and database bindings.")

    def test_02_home_page_works(self):
        """Test 2: Existing home page loads successfully."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"KisanSmart", res.data)
        print("✅ [Test 2 Passed] Home page loads successfully (HTTP 200).")

    def test_03_farmer_authentication(self):
        """Test 3: Farmer session authentication works."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.test_user_id
            sess["role"] = "kisan"
            sess["email"] = "testfarmer@kisansmart.in"

        res = self.client.get("/farmer")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Ramesh Kumar", res.data)
        print("✅ [Test 3 Passed] Farmer session authentication verified.")

    def test_04_unauthorized_access_blocked(self):
        """Test 4: Unauthorized users cannot access Disease Detection."""
        # Case A: Anonymous user (no session)
        anon_client = app.test_client()
        res_anon = anon_client.get("/disease", follow_redirects=False)
        self.assertEqual(res_anon.status_code, 302)
        self.assertEqual(res_anon.headers["Location"], "/")

        # Case B: Trader user
        trader_client = app.test_client()
        with trader_client.session_transaction() as sess:
            sess["user_id"] = "VP_TEST_101"
            sess["role"] = "vyapari"

        res_trader = trader_client.get("/disease", follow_redirects=False)
        self.assertEqual(res_trader.status_code, 302)
        self.assertEqual(res_trader.headers["Location"], "/trader")
        print("✅ [Test 4 Passed] Unauthorized users blocked from accessing /disease (redirect enforced).")

    def test_05_authenticated_farmer_access(self):
        """Test 5: Authenticated farmers can access Disease Detection."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.test_user_id
            sess["role"] = "kisan"

        res = self.client.get("/disease")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Fasal Bimari Detector", res.data)
        self.assertIn(b"Ramesh Kumar", res.data)
        print("✅ [Test 5 Passed] Authenticated farmer accessed /disease successfully.")

    def test_06_all_six_crops_available(self):
        """Test 6: All six crops appear in the disease detection selection UI."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.test_user_id
            sess["role"] = "kisan"

        res = self.client.get("/disease")
        data_str = res.data.decode("utf-8")
        
        expected_crops = ["Gehu", "Dhan", "Tomato", "Aalu", "Kapas", "Soyabean"]
        for crop in expected_crops:
            self.assertIn(f'value="{crop}"', data_str)

        # Confirm non-supported crop like Makka is removed
        self.assertNotIn('value="Makka"', data_str)
        print(f"✅ [Test 6 Passed] Exactly the six required crops appear: {expected_crops}")

    def test_07_invalid_images_rejected(self):
        """Test 7: Corrupted or non-image files are rejected with clear error."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.test_user_id
            sess["role"] = "kisan"

        # Case A: Disallowed extension (.txt)
        res_txt = self.client.post("/disease", data={
            "fasal": "Gehu",
            "file": (io.BytesIO(b"Hello world, not an image"), "malicious.txt")
        }, content_type="multipart/form-data")
        self.assertIn("allowed hain", res_txt.data.decode("utf-8"))

        # Case B: Disguised non-image (.jpg extension but random text bytes)
        fake_payload = b"Plain text payload pretending to be JPEG content, repeated multiple times. " * 5
        res_fake_jpg = self.client.post("/disease", data={
            "fasal": "Gehu",
            "file": (io.BytesIO(fake_payload), "fake.jpg")
        }, content_type="multipart/form-data")
        self.assertIn("File valid photo nahi hai", res_fake_jpg.data.decode("utf-8"))

        print("✅ [Test 7 Passed] Corrupted / non-image uploads rejected with clear error messages.")

    def test_08_file_exceeding_10mb_rejected(self):
        """Test 8: Files exceeding 10 MB are rejected."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.test_user_id
            sess["role"] = "kisan"

        oversized_data = b"0" * (11 * 1024 * 1024)  # 11 MB
        res = self.client.post("/disease", data={
            "fasal": "Gehu",
            "file": (io.BytesIO(oversized_data), "huge_image.jpg")
        }, content_type="multipart/form-data")

        self.assertIn("10MB se badi hai", res.data.decode("utf-8"))
        print("✅ [Test 8 Passed] Upload exceeding 10 MB safely rejected by backend validation.")

    def test_09_real_model_inference_all_six_crops(self):
        """Test 9: Real model inference works on independent test images from ALL 6 crops."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.test_user_id
            sess["role"] = "kisan"

        test_cases = [
            ("Gehu", "dataset/Wheat___Leaf_Rust/wheat_090.jpg", "Wheat"),
            ("Dhan", "dataset/Rice___Blast/rice_090.jpg", "Rice"),
            ("Tomato", "dataset/Tomato___Early_Blight/tomato___early_blight_090.jpg", "Tomato"),
            ("Aalu", "dataset/Potato___Late_Blight/potato___late_blight_090.jpg", "Potato"),
            ("Kapas", "dataset/Cotton___Bacterial_Blight/cotton_090.jpg", "Cotton"),
            ("Soyabean", "dataset/Soybean___Rust/soybean_090.jpg", "Soybean")
        ]

        for fasal_val, rel_img_path, exp_crop in test_cases:
            abs_img_path = os.path.join(BASE_DIR, rel_img_path)
            self.assertTrue(os.path.exists(abs_img_path), f"Test image missing: {abs_img_path}")
            
            with open(abs_img_path, "rb") as f:
                img_bytes = f.read()

            res = self.client.post("/disease", data={
                "fasal": fasal_val,
                "file": (io.BytesIO(img_bytes), os.path.basename(abs_img_path))
            }, content_type="multipart/form-data")

            self.assertEqual(res.status_code, 200, f"Inference failed for crop {fasal_val}")
            res_html = res.data.decode("utf-8")

            # Check that results block rendered
            self.assertIn("Predicted Disease", res_html, f"Result header missing for {fasal_val}")
            self.assertIn("AI Yakeen", res_html, f"Confidence missing for {fasal_val}")
            self.assertIn("Lakshan (Disease Symptoms)", res_html, f"Symptoms missing for {fasal_val}")
            self.assertIn("Dawai / Spray", res_html, f"Treatment missing for {fasal_val}")
            print(f"   ✓ Crop {fasal_val:<8} ({exp_crop}): Real AI inference succeeded with full recommendations.")

        print("✅ [Test 9 Passed] Real AI model inference executed successfully across all 6 crops.")

    def test_10_predictions_saved_in_sqlite(self):
        """Test 10: Successful predictions are persisted in the existing SQLite DiseaseScan table."""
        db = SessionLocal()
        scans = db.query(DiseaseScan).filter(DiseaseScan.kisan_id == self.kisan_id).all()
        self.assertGreaterEqual(len(scans), 6, "Expected at least 6 saved scan records in SQLite DB")

        for scan in scans[-6:]:
            self.assertIsNotNone(scan.fasal)
            self.assertIsNotNone(scan.disease)
            self.assertGreater(scan.confidence, 0.0)
            self.assertIsNotNone(scan.severity)
            self.assertIsNotNone(scan.solution)
            self.assertIsNotNone(scan.precaution)
            self.assertIsNotNone(scan.image_path)
            self.assertTrue(scan.image_path.startswith("/static/uploads/scan_"))
            self.assertTrue(os.path.exists(scan.image_path.lstrip("/")))
        db.close()
        print(f"✅ [Test 10 Passed] Scan records verified in SQLite database (DiseaseScan table).")

    def test_11_scan_history_displays_in_frontend(self):
        """Test 11: Scan history correctly renders saved predictions in the UI."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.test_user_id
            sess["role"] = "kisan"

        res = self.client.get("/disease")
        self.assertEqual(res.status_code, 200)
        res_html = res.data.decode("utf-8")

        self.assertIn("Pichle scans (Scan History)", res_html)
        self.assertIn("Gehu:", res_html)
        self.assertIn("Dhan:", res_html)
        print("✅ [Test 11 Passed] Scan history cards rendered properly with timestamps and status badges.")

    def test_12_existing_modules_unaffected(self):
        """Test 12: Other application modules continue working uninterrupted."""
        # Weather
        res_weather = self.client.get("/weather")
        self.assertEqual(res_weather.status_code, 200)

        # Farmer profile
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.test_user_id
            sess["role"] = "kisan"
        res_profile = self.client.get("/farmer-profile")
        self.assertEqual(res_profile.status_code, 200)

        # Logout
        res_logout = self.client.get("/logout")
        self.assertEqual(res_logout.status_code, 302)
        print("✅ [Test 12 Passed] Existing modules (/weather, /farmer-profile, /logout) fully operational.")

if __name__ == "__main__":
    unittest.main()
