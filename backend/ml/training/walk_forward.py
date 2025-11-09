"""Walk-forward validation utilities with support for deep learning models."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Tuple, Dict, List, Optional, Any
import numpy as np
import pandas as pd
from backend.ml.baselines import baseline_models
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class WalkForwardSplit:
    train_indices: Tuple[int, int]
    test_indices: Tuple[int, int]
    split_id: int = 0


@dataclass
class WalkForwardResult:
    """Results from walk-forward validation"""
    split_id: int
    train_size: int
    test_size: int
    model_metrics: Dict[str, float]
    baseline_metrics: Dict[str, float]
    beats_baseline: bool
    improvement_pct: float


class WalkForwardSplitter:
    """Generate expanding window walk-forward splits."""

    def __init__(self, n_splits: int, test_size: int):
        if n_splits < 1:
            raise ValueError("n_splits must be >= 1")
        self.n_splits = n_splits
        self.test_size = test_size

    def split(self, df: pd.DataFrame) -> Iterator[WalkForwardSplit]:
        n_samples = len(df)
        if n_samples <= self.test_size * (self.n_splits + 1):
            raise ValueError("Dataset too small for requested splits")

        start = 0
        for split in range(self.n_splits):
            train_end = self.test_size * (split + 1)
            test_start = train_end
            test_end = test_start + self.test_size
            yield WalkForwardSplit(
                train_indices=(start, train_end),
                test_indices=(test_start, min(test_end, n_samples)),
                split_id=split
            )

    def summarize(self, df: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for split_id, split in enumerate(self.split(df)):
            rows.append(
                {
                    "split": split_id,
                    "train_start": split.train_indices[0],
                    "train_end": split.train_indices[1],
                    "test_start": split.test_indices[0],
                    "test_end": split.test_indices[1],
                }
            )
        return pd.DataFrame(rows)
    
    async def validate_model(
        self,
        df: pd.DataFrame,
        model_trainer: Any,
        model_type: str = "generic"
    ) -> List[WalkForwardResult]:
        """
        Run walk-forward validation on a model trainer.
        
        Args:
            df: Full dataset with 'close' column
            model_trainer: Object with train_and_score(train_df, test_df) method
            model_type: Type of model for logging
        
        Returns:
            List of WalkForwardResult for each split
        """
        results = []
        
        logger.info(f"Starting walk-forward validation: {self.n_splits} splits, test_size={self.test_size}")
        
        for split in self.split(df):
            train_df = df.iloc[split.train_indices[0]:split.train_indices[1]].copy()
            test_df = df.iloc[split.test_indices[0]:split.test_indices[1]].copy()
            
            # Train and score model
            try:
                model_metrics, _ = model_trainer.train_and_score(train_df, test_df)
            except Exception as e:
                logger.error(f"Split {split.split_id} training failed: {e}")
                model_metrics = {"error": str(e)}
                continue
            
            # Compute baseline comparison
            baseline_comparison = baseline_models.compare_with_baselines(
                model_metrics,
                train_df,
                test_df
            )
            
            result = WalkForwardResult(
                split_id=split.split_id,
                train_size=len(train_df),
                test_size=len(test_df),
                model_metrics=model_metrics,
                baseline_metrics=baseline_comparison['baselines'],
                beats_baseline=baseline_comparison['beats_baseline'],
                improvement_pct=baseline_comparison['improvement_pct']
            )
            
            results.append(result)
            
            logger.info(
                f"Split {split.split_id}: RMSE={model_metrics.get('rmse', 'N/A')}, "
                f"Beats baseline: {result.beats_baseline}, "
                f"Improvement: {result.improvement_pct:.1f}%"
            )
        
        return results
    
    def aggregate_results(self, results: List[WalkForwardResult]) -> Dict:
        """Aggregate walk-forward results across all splits"""
        if not results:
            return {"error": "no_results"}
        
        rmse_scores = [r.model_metrics.get('rmse') for r in results if 'rmse' in r.model_metrics]
        mae_scores = [r.model_metrics.get('mae') for r in results if 'mae' in r.model_metrics]
        improvements = [r.improvement_pct for r in results]
        beats_baseline_count = sum(1 for r in results if r.beats_baseline)
        
        return {
            "n_splits": len(results),
            "avg_rmse": float(np.mean(rmse_scores)) if rmse_scores else None,
            "std_rmse": float(np.std(rmse_scores)) if rmse_scores else None,
            "avg_mae": float(np.mean(mae_scores)) if mae_scores else None,
            "avg_improvement_pct": float(np.mean(improvements)),
            "beats_baseline_count": beats_baseline_count,
            "beats_baseline_rate": float(beats_baseline_count / len(results)) if results else 0.0,
            "all_splits_beat_baseline": beats_baseline_count == len(results)
        }
