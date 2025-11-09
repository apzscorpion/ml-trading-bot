import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytz

from backend.data_pipeline import DataPipeline, FeatureStore
from backend.data_pipeline.config import get_config


class DataPipelineIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="pipeline-tests-")
        self.config = get_config(self.tmp_dir)
        self.pipeline = DataPipeline(config=self.config)
        self.symbol = "TCS.NS"
        self.timeframe = "5m"
        self.ist = pytz.timezone("Asia/Kolkata")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _build_candles(self, count: int = 40):
        base_time = self.ist.localize(datetime(2025, 11, 5, 9, 15))
        candles = []
        for idx in range(count):
            start_ts = base_time + timedelta(minutes=5 * idx)
            candles.append(
                {
                    "start_ts": start_ts.isoformat(),
                    "open": 3250.0 + idx,
                    "high": 3255.0 + idx,
                    "low": 3245.0 + idx,
                    "close": 3252.0 + idx,
                    "volume": 100000 + idx * 10,
                }
            )
        return candles

    def test_ingest_creates_all_layers(self):
        candles = self._build_candles()
        artifacts = self.pipeline.ingest(
            symbol=self.symbol,
            timeframe=self.timeframe,
            candles=candles,
            provider="unit-test",
            dataset_version="test-v1",
        )

        self.assertTrue(Path(artifacts.raw_path).exists())
        self.assertTrue(Path(artifacts.bronze_path).exists())
        self.assertTrue(Path(artifacts.silver_path).exists())
        self.assertGreater(artifacts.record_count, 0)

        silver_df = pd.read_parquet(artifacts.silver_path)
        expected_columns = {
            "start_ts",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "return_1",
            "return_5",
            "rolling_mean_10",
            "rolling_std_10",
            "volume_ma_10",
            "high_low_spread",
            "momentum_10",
            "ema_20",
            "is_gap_up",
            "is_gap_down",
        }
        self.assertTrue(expected_columns.issubset(set(silver_df.columns)))

    def test_feature_store_loads_latest(self):
        candles = self._build_candles()
        artifacts = self.pipeline.ingest(
            symbol=self.symbol,
            timeframe=self.timeframe,
            candles=candles,
            provider="unit-test",
            dataset_version="test-v2",
        )

        store = FeatureStore(config=self.config)
        latest = store.load_features(symbol=self.symbol, timeframe=self.timeframe)
        self.assertIsNotNone(latest)
        assert latest is not None
        self.assertEqual(len(latest), artifacts.record_count)

        window = store.load_time_window(
            symbol=self.symbol,
            timeframe=self.timeframe,
            window_minutes=60,
            as_of=self.ist.localize(datetime(2025, 11, 5, 12, 0)),
        )
        self.assertIsNotNone(window)
        if window is not None:
            self.assertLessEqual(window["start_ts"].iloc[0], window["start_ts"].iloc[-1])


if __name__ == "__main__":
    unittest.main()
