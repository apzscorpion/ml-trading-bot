import shutil
import tempfile
import unittest
from datetime import datetime, timedelta

import pytz

from backend.data_pipeline.config import get_config as get_data_config
from backend.data_pipeline.ingestion import DataPipeline
from backend.ml.training.config import get_config as get_training_config
from backend.ml.training.orchestrator import TrainingOrchestrator


class TrainingOrchestratorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_root = tempfile.mkdtemp(prefix="orch-tests-")
        self.data_config = get_data_config(self.tmp_root)
        self.pipeline = DataPipeline(config=self.data_config)
        self.symbol = "TCS.NS"
        self.timeframe = "5m"
        self._ingest_sample()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def _ingest_sample(self):
        ist = pytz.timezone("Asia/Kolkata")
        base = ist.localize(datetime(2025, 11, 5, 9, 15))
        candles = []
        for idx in range(400):
            ts = base + timedelta(minutes=5 * idx)
            candles.append(
                {
                    "start_ts": ts.isoformat(),
                    "open": 3200 + idx * 0.5,
                    "high": 3205 + idx * 0.5,
                    "low": 3195 + idx * 0.5,
                    "close": 3202 + idx * 0.5,
                    "volume": 100000 + idx * 5,
                }
            )
        self.pipeline.ingest(
            symbol=self.symbol,
            timeframe=self.timeframe,
            candles=candles,
            provider="unit-test",
            dataset_version="test-suite",
        )

    def test_orchestrator_returns_metrics(self):
        training_cfg = get_training_config(
            experiments_root=f"{self.tmp_root}/experiments",
            data_root=self.tmp_root,
        )
        orchestrator = TrainingOrchestrator(config=training_cfg)
        result = orchestrator.train(
            symbol=self.symbol,
            timeframe=self.timeframe,
            dataset_version="test-suite",
            families=["baseline", "random_forest"],
        )

        self.assertTrue(result.metrics)
        self.assertIn("baseline", result.metrics)
        self.assertIn("random_forest", result.metrics)
        self.assertGreater(result.metrics["baseline"]["mae"], 0)
        self.assertIn("registry_path", result.artifacts)


if __name__ == "__main__":
    unittest.main()
