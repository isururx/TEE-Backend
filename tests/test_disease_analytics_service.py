from datetime import date, datetime
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import Disease, DiseaseDetection, PlantationBlock, User
from app.services.analytics.disease_analytics_service import (
    get_disease_analytics_summary,
)


class DiseaseAnalyticsServiceTestCase(unittest.TestCase):
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

        self.user = User(
            id=1,
            name="analytics-test-user",
            email="analytics-test@tee.lk",
            password="test-password",
            role="Admin",
            is_active=True,
        )
        self.diseases = [
            Disease(id=1, name="Brown Blight"),
            Disease(id=2, name="Gray Blight"),
            Disease(id=3, name="Healthy leaf"),
        ]
        self.blocks = [
            PlantationBlock(id=1, area=10.0),
            PlantationBlock(id=2, area=8.0),
            PlantationBlock(id=3, area=5.0),
        ]
        self.db.add_all([self.user, *self.diseases, *self.blocks])
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _add_detection(self, disease_id, block_id, day, hour=12):
        self.db.add(
            DiseaseDetection(
                disease_id=disease_id,
                user_id=self.user.id,
                block_id=block_id,
                image_path="uploads/test-image.jpg",
                confidence_score=0.9,
                timestamp=datetime(2026, 11, day, hour, 0, 0),
            )
        )
        self.db.commit()

    def test_aggregates_diseases_blocks_healthy_and_unassigned_events(self):
        self._add_detection(1, 1, 1)
        self._add_detection(1, 1, 2)
        self._add_detection(3, 1, 2)
        self._add_detection(1, 2, 3)
        self._add_detection(2, 2, 3)
        self._add_detection(2, None, 3)

        result = get_disease_analytics_summary(self.db)

        self.assertEqual(
            result["summary"],
            {
                "total_detections": 6,
                "diseased_detections": 5,
                "healthy_detections": 1,
                "unassigned_detections": 1,
            },
        )
        self.assertEqual(len(result["blocks"]), 3)
        self.assertEqual(result["blocks"][0]["total_detections"], 3)
        self.assertEqual(
            result["blocks"][0]["most_frequently_detected_diseases"],
            ["Brown Blight"],
        )
        self.assertEqual(
            result["blocks"][1]["most_frequently_detected_diseases"],
            ["Brown Blight", "Gray Blight"],
        )
        self.assertEqual(result["blocks"][2]["total_detections"], 0)
        self.assertEqual(
            [(item["disease_name"], item["frequency"])
             for item in result["disease_distribution"]],
            [("Brown Blight", 3), ("Gray Blight", 2)],
        )
        self.assertEqual(
            [item["block_id"] for item in result["highest_frequency_blocks"]],
            [1, 2],
        )

    def test_date_range_is_inclusive_and_optional_filters_are_applied(self):
        self._add_detection(1, 1, 1, 1)
        self._add_detection(1, 1, 2, 23)
        self._add_detection(2, 2, 3, 0)

        result = get_disease_analytics_summary(
            self.db,
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 2),
            block_id=1,
            disease_id=1,
        )

        self.assertEqual(result["summary"]["total_detections"], 1)
        self.assertEqual(result["summary"]["diseased_detections"], 1)
        self.assertEqual(result["blocks"][0]["block_id"], 1)
        self.assertEqual(result["blocks"][0]["diseases"][0]["frequency"], 1)
        self.assertEqual(
            result["period"],
            {
                "start_date": "2026-11-02",
                "end_date": "2026-11-02",
                "timezone": "UTC",
            },
        )

    def test_invalid_date_range_is_rejected(self):
        with self.assertRaises(ValueError):
            get_disease_analytics_summary(
                self.db,
                start_date=date(2026, 11, 27),
                end_date=date(2026, 11, 26),
            )


if __name__ == "__main__":
    unittest.main()
