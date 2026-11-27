from datetime import date, datetime
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies.auth import get_current_user
from app.db.database import Base, get_db
from app.db.models.detection import DiseaseDetection
from app.db.models.disease import Disease
from app.db.models.plantation_block import PlantationBlock
from app.db.models.user import User
from app.main import app


class DiseaseAnalyticsApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.Session = sessionmaker(
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
        self.db = self.Session()
        for table in reversed(Base.metadata.sorted_tables):
            self.db.execute(table.delete())
        self.db.commit()

        self.admin = User(
            id=1, name="Admin", email="api-admin@tee.lk",
            password="test", role="Admin", is_active=True,
        )
        self.supervisor = User(
            id=2, name="Supervisor", email="api-supervisor@tee.lk",
            password="test", role="Supervisor", is_active=True,
        )
        self.other_supervisor = User(
            id=3, name="Other Supervisor", email="api-other@tee.lk",
            password="test", role="Supervisor", is_active=True,
        )
        self.worker = User(
            id=4, name="Worker", email="api-worker@tee.lk",
            password="test", role="Worker", is_active=True,
        )
        self.db.add_all([
            self.admin, self.supervisor, self.other_supervisor, self.worker,
            Disease(id=1, name="Brown Blight"),
            Disease(id=2, name="Gray Blight"),
            Disease(id=3, name="Healthy leaf"),
            PlantationBlock(id=1, area=10.0, supervisor_id=2),
            PlantationBlock(id=2, area=8.0, supervisor_id=3),
        ])
        self.db.flush()
        self.db.add_all([
            DiseaseDetection(
                disease_id=1, user_id=1, block_id=1,
                image_path="test-1.jpg", confidence_score=0.9,
                timestamp=datetime(2026, 11, 10, 12, 0),
            ),
            DiseaseDetection(
                disease_id=2, user_id=1, block_id=1,
                image_path="test-2.jpg", confidence_score=0.8,
                timestamp=datetime(2026, 11, 11, 12, 0),
            ),
            DiseaseDetection(
                disease_id=3, user_id=1, block_id=1,
                image_path="test-3.jpg", confidence_score=0.99,
                timestamp=datetime(2026, 11, 12, 12, 0),
            ),
            DiseaseDetection(
                disease_id=1, user_id=1, block_id=None,
                image_path="test-4.jpg", confidence_score=0.9,
                timestamp=datetime(2026, 11, 13, 12, 0),
            ),
        ])
        self.db.commit()

        self.current_user = self.admin

        def override_db():
            yield self.db

        def override_user():
            return self.current_user

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = override_user
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()

    def test_frequency_by_block_returns_database_aggregates(self):
        response = self.client.get("/api/analytics/disease-frequency-by-block")
        self.assertEqual(response.status_code, 200, msg=response.text)
        data = response.json()
        self.assertEqual(data["summary"]["total_detections"], 4)
        self.assertEqual(data["summary"]["diseased_detections"], 3)
        self.assertEqual(data["summary"]["healthy_detections"], 1)
        self.assertEqual(data["summary"]["unassigned_detections"], 1)
        self.assertEqual(len(data["blocks"]), 2)
        self.assertEqual(data["blocks"][0]["total_detections"], 3)
        self.assertEqual(
            [item["disease_name"] for item in data["blocks"][0]["diseases"]],
            ["Brown Blight", "Gray Blight"],
        )

    def test_distribution_excludes_healthy_leaf(self):
        response = self.client.get("/api/analytics/disease-distribution")
        self.assertEqual(response.status_code, 200, msg=response.text)
        data = response.json()
        self.assertEqual(
            [item["disease_name"] for item in data["disease_distribution"]],
            ["Brown Blight", "Gray Blight"],
        )
        self.assertEqual(data["disease_distribution"][0]["affected_blocks"], 1)

    def test_block_summary_requires_block_and_includes_zero_count_block(self):
        response = self.client.get(
            "/api/analytics/block-disease-summary",
            params={"block_id": 2},
        )
        self.assertEqual(response.status_code, 200, msg=response.text)
        self.assertEqual(response.json()["block"]["total_detections"], 0)

    def test_date_and_disease_filters_are_applied(self):
        response = self.client.get(
            "/api/analytics/disease-frequency-by-block",
            params={
                "start_date": "2026-11-11",
                "end_date": "2026-11-11",
                "disease_id": 2,
            },
        )
        self.assertEqual(response.status_code, 200, msg=response.text)
        self.assertEqual(response.json()["summary"]["total_detections"], 1)

    def test_invalid_date_range_returns_422(self):
        response = self.client.get(
            "/api/analytics/disease-frequency-by-block",
            params={"start_date": "2026-11-20", "end_date": "2026-11-01"},
        )
        self.assertEqual(response.status_code, 422)

    def test_invalid_block_and_disease_ids_return_404(self):
        block_response = self.client.get(
            "/api/analytics/disease-frequency-by-block",
            params={"block_id": 999},
        )
        disease_response = self.client.get(
            "/api/analytics/disease-frequency-by-block",
            params={"disease_id": 999},
        )
        self.assertEqual(block_response.status_code, 404)
        self.assertEqual(disease_response.status_code, 404)

    def test_supervisor_can_only_view_their_own_block(self):
        self.current_user = self.supervisor
        allowed = self.client.get(
            "/api/analytics/block-disease-summary",
            params={"block_id": 1},
        )
        forbidden = self.client.get(
            "/api/analytics/block-disease-summary",
            params={"block_id": 2},
        )
        estate_wide = self.client.get(
            "/api/analytics/disease-frequency-by-block",
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(estate_wide.status_code, 403)

    def test_worker_is_forbidden(self):
        self.current_user = self.worker
        response = self.client.get("/api/analytics/disease-frequency-by-block")
        self.assertEqual(response.status_code, 403)

    def test_missing_authentication_is_rejected(self):
        app.dependency_overrides.pop(get_current_user, None)
        response = self.client.get("/api/analytics/disease-frequency-by-block")
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
