import unittest
from datetime import datetime, timedelta

from backend.monitoring.drift_monitor import DriftMonitor


class DriftMonitorTest(unittest.TestCase):
    def test_compute_metrics(self):
        monitor = DriftMonitor()
        base_time = datetime(2025, 11, 5, 9, 15)
        prediction = {
            'predicted_series': [
                {'ts': (base_time + timedelta(minutes=5 * i)).isoformat(), 'price': 3200 + i}
                for i in range(10)
            ]
        }
        actual = [
            {
                'start_ts': (base_time + timedelta(minutes=5 * i)).isoformat(),
                'close': 3200 + i * 1.1,
            }
            for i in range(10)
        ]
        metrics = monitor.compute(prediction, actual)
        self.assertGreater(metrics.mae, 0)
        self.assertGreaterEqual(metrics.directional_accuracy, 0)
        self.assertTrue(metrics.mape >= 0)


if __name__ == '__main__':
    unittest.main()
