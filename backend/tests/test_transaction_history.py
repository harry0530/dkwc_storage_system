import datetime as dt
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.database import Base
from app.routes.transaction import get_transaction_history


class TransactionHistoryTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

        self.db.add(models.Product(new_code="P-100", name="테스트 후크", type="PART"))
        reconstructed = models.Transaction(
            product_code="P-100", quantity=12, type="IN",
            reason="HISTORICAL_RECONSTRUCTION:test.xlsx:2024:10",
            created_at=dt.datetime(2024, 3, 1, 12, 0),
        )
        direct = models.Transaction(
            product_code="P-100", quantity=2, type="OUT", reason="SHIPMENT",
            created_at=dt.datetime(2024, 3, 2, 12, 0),
        )
        self.db.add_all([reconstructed, direct])
        self.db.flush()
        self.db.add(models.HistoricalImport(
            fingerprint="history-test-1", source_file="금명특장 PROFORMA.xlsx",
            source_sheet="2024-03", source_row=10, event_type="IN",
            event_date=reconstructed.created_at, product_code="P-100", quantity=12,
            company="금명특장", transaction_id=reconstructed.id,
        ))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def get_history(self, **overrides):
        params = {
            "page": 1, "page_size": 10, "search": "", "transaction_type": "",
            "start_date": None, "end_date": None, "reconstructed_only": False,
            "db": self.db,
        }
        params.update(overrides)
        return get_transaction_history(**params)

    def test_returns_paginated_summary_and_provenance(self):
        result = self.get_history()
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["summary"]["in_quantity"], 12)
        self.assertEqual(result["summary"]["out_quantity"], 2)
        self.assertFalse(result["items"][0]["is_reconstructed"])
        self.assertTrue(result["items"][1]["is_reconstructed"])
        self.assertEqual(result["items"][1]["company"], "금명특장")

    def test_filters_reconstructed_records_by_company(self):
        result = self.get_history(search="금명", reconstructed_only=True)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["source_file"], "금명특장 PROFORMA.xlsx")


if __name__ == "__main__":
    unittest.main()
