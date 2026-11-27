from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from jose import jwt
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import ALGORITHM, SECRET_KEY, create_access_token
from app.db.database import Base, get_db
from app.db.models.detection import DiseaseDetection
from app.db.models.disease import Disease
from app.db.models.plantation_block import PlantationBlock
from app.db.models.user import User
from app.db.models.worker import Worker
from app.main import app
from app.ml.model import CLASS_NAMES
from app.services import detection_service


def _make_test_image_bytes(fmt: str = "JPEG") -> bytes:
    buf = BytesIO()
    img = Image.new("RGB", (32, 32), color=(34, 139, 34))
    img.save(buf, format=fmt)
    return buf.getvalue()


class DetectionPhase1TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.TestingSessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=cls.engine,
        )
        Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()

    def setUp(self):
        self.db = self.TestingSessionLocal()
        for table in reversed(Base.metadata.sorted_tables):
            self.db.execute(table.delete())
        self.db.commit()

        for idx, name in enumerate(CLASS_NAMES, start=1):
            self.db.add(Disease(id=idx, name=name, description=f"{name} description"))

        self.admin = User(id=1, name="admin_user", email="admin@tee.lk", password="pw", role="Admin", is_active=True)
        self.manager = User(id=2, name="manager_user", email="manager@tee.lk", password="pw", role="Manager", is_active=True)
        self.sup_a = User(id=3, name="sup_a", email="supa@tee.lk", password="pw", role="Supervisor", is_active=True)
        self.sup_b = User(id=4, name="sup_b", email="supb@tee.lk", password="pw", role="supervisor", is_active=True)
        self.worker_assigned = User(id=5, name="worker_a", email="workera@tee.lk", password="pw", role="Worker", is_active=True)
        self.worker_unassigned = User(id=6, name="worker_b", email="workerb@tee.lk", password="pw", role="Field Worker", is_active=True)
        self.inactive_user = User(id=7, name="inactive", email="inactive@tee.lk", password="pw", role="Admin", is_active=False)
        self.unknown_role_user = User(id=8, name="guest", email="guest@tee.lk", password="pw", role="Guest", is_active=True)

        self.db.add_all([
            self.admin, self.manager, self.sup_a, self.sup_b,
            self.worker_assigned, self.worker_unassigned,
            self.inactive_user, self.unknown_role_user,
        ])
        self.db.flush()

        self.block_1 = PlantationBlock(id=1, area=10.5, tea_variety="TRI 2025", supervisor_id=self.sup_a.id)
        self.block_2 = PlantationBlock(id=2, area=8.0, tea_variety="B.O.P. Hybrid", supervisor_id=self.sup_b.id)
        self.block_unowned = PlantationBlock(id=3, area=5.0, tea_variety="TV-1", supervisor_id=None)
        self.db.add_all([self.block_1, self.block_2, self.block_unowned])
        self.db.flush()

        self.worker_row = Worker(
            id=self.worker_assigned.id,
            name="worker_a",
            NIC=199912345678,
            dob=date(1999, 1, 1),
            address="Estate Line 1",
            email="workera@tee.lk",
            phone_num=771234567,
            assigned_block=self.block_1.id,
            password="pw",
        )
        self.db.add(self.worker_row)
        self.db.commit()

        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        self.temp_dir = tempfile.TemporaryDirectory()
        self.upload_patcher = patch.object(detection_service, "UPLOAD_DIR", Path(self.temp_dir.name))
        self.upload_patcher.start()

    def tearDown(self):
        self.upload_patcher.stop()
        self.temp_dir.cleanup()
        app.dependency_overrides.clear()
        self.db.close()

    def _auth_header(self, user: User) -> dict:
        token = create_access_token(user_id=user.id, role=user.role)
        return {"Authorization": f"Bearer {token}"}

    def _post_detection(self, user: User, data=None):
        return self.client.post(
            "/api/detection/detect",
            headers=self._auth_header(user),
            data=data or {},
            files={"image": ("leaf.jpg", _make_test_image_bytes(), "image/jpeg")},
        )

    def test_missing_token_rejected(self):
        res = self.client.post(
            "/api/detection/detect",
            data={"block_id": "1"},
            files={"image": ("leaf.jpg", _make_test_image_bytes(), "image/jpeg")},
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(self.db.query(DiseaseDetection).count(), 0)

    def test_invalid_token_rejected(self):
        res = self.client.post(
            "/api/detection/detect",
            headers={"Authorization": "Bearer invalid.jwt.token"},
            data={"block_id": "1"},
            files={"image": ("leaf.jpg", _make_test_image_bytes(), "image/jpeg")},
        )
        self.assertEqual(res.status_code, 401)

    def test_expired_token_rejected(self):
        expired_payload = {
            "sub": str(self.admin.id),
            "role": self.admin.role,
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        }
        expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
        res = self.client.post(
            "/api/detection/detect",
            headers={"Authorization": f"Bearer {expired_token}"},
            data={"block_id": "1"},
            files={"image": ("leaf.jpg", _make_test_image_bytes(), "image/jpeg")},
        )
        self.assertEqual(res.status_code, 401)

    def test_non_numeric_sub_claim_rejected_cleanly(self):
        bad_token = jwt.encode(
            {"sub": "not-an-int", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
            SECRET_KEY,
            algorithm=ALGORITHM,
        )
        res = self.client.post(
            "/api/detection/detect",
            headers={"Authorization": f"Bearer {bad_token}"},
            data={"block_id": "1"},
            files={"image": ("leaf.jpg", _make_test_image_bytes(), "image/jpeg")},
        )
        self.assertEqual(res.status_code, 401)

    def test_inactive_user_rejected(self):
        res = self._post_detection(self.inactive_user, {"block_id": "1"})
        self.assertEqual(res.status_code, 403)

    def test_missing_block_id_is_saved_as_unassigned_for_estate_manager(self):
        with patch.object(detection_service, "predict_image", return_value=("Brown Blight", 0.91)):
            res = self._post_detection(self.admin)
        self.assertEqual(res.status_code, 200, msg=res.text)
        saved = self.db.query(DiseaseDetection).filter(DiseaseDetection.id == res.json()["detection_id"]).first()
        self.assertIsNotNone(saved)
        self.assertIsNone(saved.block_id)
        self.assertEqual(saved.user_id, self.admin.id)

    def test_unassigned_detection_is_forbidden_for_supervisor_and_worker(self):
        for user in (self.sup_a, self.worker_assigned):
            res = self._post_detection(user)
            self.assertEqual(res.status_code, 403)
        self.assertEqual(self.db.query(DiseaseDetection).count(), 0)

    def test_nonexistent_block_returns_404(self):
        res = self._post_detection(self.admin, {"block_id": "9999"})
        self.assertEqual(res.status_code, 404)

    def test_supervisor_cannot_detect_for_other_supervisors_block(self):
        res = self._post_detection(self.sup_a, {"block_id": str(self.block_2.id)})
        self.assertEqual(res.status_code, 403)
        self.assertEqual(self.db.query(DiseaseDetection).count(), 0)

    def test_supervisor_cannot_detect_for_unowned_block(self):
        res = self._post_detection(self.sup_a, {"block_id": str(self.block_unowned.id)})
        self.assertEqual(res.status_code, 403)

    def test_worker_cannot_detect_for_unassigned_block(self):
        res = self._post_detection(self.worker_assigned, {"block_id": str(self.block_2.id)})
        self.assertEqual(res.status_code, 403)

    def test_worker_without_worker_profile_cannot_detect(self):
        res = self._post_detection(self.worker_unassigned, {"block_id": str(self.block_1.id)})
        self.assertEqual(res.status_code, 403)

    def test_unknown_role_cannot_detect(self):
        res = self._post_detection(self.unknown_role_user, {"block_id": str(self.block_1.id)})
        self.assertEqual(res.status_code, 403)

    @patch.object(detection_service, "predict_image", return_value=("Brown Blight", 0.91))
    def test_authorized_roles_succeed_and_ignore_spoofed_user_id(self, _mock_predict):
        authorized_cases = [
            (self.admin, self.block_2.id),
            (self.manager, self.block_2.id),
            (self.sup_a, self.block_1.id),
            (self.worker_assigned, self.block_1.id),
        ]
        for user, block_id in authorized_cases:
            res = self.client.post(
                "/api/detection/detect",
                headers=self._auth_header(user),
                data={"block_id": str(block_id), "user_id": "999"},
                files={"image": ("leaf.jpg", _make_test_image_bytes(), "image/jpeg")},
            )
            self.assertEqual(res.status_code, 200, msg=f"Failed for role {user.role}: {res.text}")
            saved = self.db.query(DiseaseDetection).filter(DiseaseDetection.id == res.json()["detection_id"]).first()
            self.assertEqual(saved.user_id, user.id)
            self.assertEqual(saved.block_id, block_id)
            self.assertEqual(saved.disease_id, 1)
            self.assertAlmostEqual(saved.confidence_score, 0.91, places=5)
            self.assertIsNotNone(saved.timestamp)
            self.assertTrue(Path(saved.image_path).exists())

    @patch.object(detection_service, "predict_image", return_value=("Healthy leaf", 0.965))
    def test_healthy_leaf_prediction(self, _mock_predict):
        res = self.client.post(
            "/api/detection/detect",
            headers=self._auth_header(self.sup_a),
            data={"block_id": str(self.block_1.id)},
            files={"image": ("leaf.png", _make_test_image_bytes("PNG"), "image/png")},
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["is_healthy"])
        saved = self.db.query(DiseaseDetection).filter(DiseaseDetection.id == res.json()["detection_id"]).first()
        self.assertEqual(saved.disease_id, 4)

    @patch.object(detection_service, "predict_image", return_value=("Unknown Disease", 0.80))
    def test_unknown_disease_label_returns_422_without_saving(self, _mock_predict):
        res = self.client.post(
            "/api/detection/detect",
            headers=self._auth_header(self.admin),
            data={"block_id": str(self.block_1.id)},
            files={"image": ("leaf.jpg", _make_test_image_bytes(), "image/jpeg")},
        )
        self.assertEqual(res.status_code, 422)
        self.assertEqual(self.db.query(DiseaseDetection).count(), 0)
        self.assertEqual(list(Path(self.temp_dir.name).iterdir()), [])

    def test_invalid_mime_type_returns_400(self):
        res = self.client.post(
            "/api/detection/detect",
            headers=self._auth_header(self.admin),
            data={"block_id": str(self.block_1.id)},
            files={"image": ("notes.txt", b"not an image", "text/plain")},
        )
        self.assertEqual(res.status_code, 400)

    def test_unsupported_image_format_returns_415(self):
        res = self.client.post(
            "/api/detection/detect",
            headers=self._auth_header(self.admin),
            data={"block_id": str(self.block_1.id)},
            files={"image": ("leaf.gif", b"GIF89a", "image/gif")},
        )
        self.assertEqual(res.status_code, 415)

    def test_corrupted_image_bytes_returns_400(self):
        res = self.client.post(
            "/api/detection/detect",
            headers=self._auth_header(self.admin),
            data={"block_id": str(self.block_1.id)},
            files={"image": ("corrupt.jpg", b"not-valid-jpeg-bytes", "image/jpeg")},
        )
        self.assertEqual(res.status_code, 400)

    @patch.object(detection_service, "predict_image", side_effect=RuntimeError("sensitive internal trace"))
    def test_cnn_failure_returns_500_without_leaking_details_or_saving_record(self, _mock_predict):
        res = self.client.post(
            "/api/detection/detect",
            headers=self._auth_header(self.admin),
            data={"block_id": str(self.block_1.id)},
            files={"image": ("leaf.jpg", _make_test_image_bytes(), "image/jpeg")},
        )
        self.assertEqual(res.status_code, 500)
        self.assertNotIn("sensitive internal trace", res.text)
        self.assertEqual(self.db.query(DiseaseDetection).count(), 0)
        self.assertEqual(list(Path(self.temp_dir.name).iterdir()), [])

    def test_existing_auth_and_blocks_endpoints_remain_functional(self):
        protected_res = self.client.get("/api/auth/protected", headers=self._auth_header(self.sup_a))
        self.assertEqual(protected_res.status_code, 200)
        self.assertEqual(protected_res.json()["user"]["id"], self.sup_a.id)
        blocks_res = self.client.get("/api/blocks")
        self.assertEqual(blocks_res.status_code, 200)
        self.assertEqual(len(blocks_res.json()), 3)


if __name__ == "__main__":
    unittest.main()
