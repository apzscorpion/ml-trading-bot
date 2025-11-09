"""
Model & Data Validation Diagnostic Script

This script helps diagnose common issues with trading prediction models:
1. Time horizon misalignment
2. Data quality and volume issues
3. Unrealistic predictions
4. Feature leakage
5. Target distribution problems

Run this before trusting any model predictions.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import SessionLocal, Candle, Prediction
from utils.logger import get_logger

logger = get_logger(__name__)


class ModelDiagnostics:
    """Comprehensive model and data diagnostics"""
    
    def __init__(self, symbol: str, timeframe: str):
        self.symbol = symbol
        self.timeframe = timeframe
        self.db = SessionLocal()
    
    def run_full_diagnostics(self) -> Dict:
        """Run all diagnostic checks"""
        print("\n" + "="*80)
        print(f"🔍 MODEL DIAGNOSTICS: {self.symbol} / {self.timeframe}")
        print("="*80 + "\n")
        
        results = {}
        
        # 1. Data volume check
        print("📊 1. DATA VOLUME CHECK")
        results['data_volume'] = self.check_data_volume()
        self._print_results(results['data_volume'])
        
        # 2. Time horizon validation
        print("\n⏰ 2. TIME HORIZON VALIDATION")
        results['time_horizon'] = self.validate_time_horizon()
        self._print_results(results['time_horizon'])
        
        # 3. Return distribution analysis
        print("\n📈 3. RETURN DISTRIBUTION ANALYSIS")
        results['return_distribution'] = self.analyze_return_distribution()
        self._print_results(results['return_distribution'])
        
        # 4. Prediction sanity check
        print("\n🎯 4. PREDICTION SANITY CHECK")
        results['prediction_sanity'] = self.check_prediction_sanity()
        self._print_results(results['prediction_sanity'])
        
        # 5. Feature leakage detection
        print("\n🔒 5. FEATURE LEAKAGE DETECTION")
        results['leakage'] = self.detect_feature_leakage()
        self._print_results(results['leakage'])
        
        # 6. Regime coverage
        print("\n🌊 6. REGIME COVERAGE ANALYSIS")
        results['regime_coverage'] = self.analyze_regime_coverage()
        self._print_results(results['regime_coverage'])
        
        # 7. Overall assessment
        print("\n" + "="*80)
        print("📋 OVERALL ASSESSMENT")
        print("="*80)
        self._print_overall_assessment(results)
        
        return results
    
    def check_data_volume(self) -> Dict:
        """Check if we have sufficient data"""
        candles = self.db.query(Candle).filter(
            Candle.symbol == self.symbol,
            Candle.timeframe == self.timeframe
        ).order_by(Candle.start_ts).all()
        
        if not candles:
            return {
                'status': 'CRITICAL',
                'total_candles': 0,
                'message': 'No data found!',
                'recommendations': ['Fetch historical data first']
            }
        
        df = pd.DataFrame([{
            'start_ts': c.start_ts,
            'close': c.close,
            'volume': c.volume
        } for c in candles])
        
        # Calculate time span
        time_span = (df['start_ts'].max() - df['start_ts'].min()).days
        
        # Recommended minimum samples
        timeframe_mins = self._timeframe_to_minutes(self.timeframe)
        recommended_days = 90  # 3 months minimum
        recommended_samples = (recommended_days * 24 * 60) / timeframe_mins
        
        status = 'OK' if len(df) >= recommended_samples else 'WARNING'
        if len(df) < recommended_samples * 0.3:
            status = 'CRITICAL'
        
        return {
            'status': status,
            'total_candles': len(df),
            'time_span_days': time_span,
            'recommended_samples': int(recommended_samples),
            'coverage_pct': (len(df) / recommended_samples * 100) if recommended_samples > 0 else 0,
            'start_date': df['start_ts'].min(),
            'end_date': df['start_ts'].max(),
            'recommendations': self._get_data_volume_recommendations(len(df), recommended_samples)
        }
    
    def validate_time_horizon(self) -> Dict:
        """Validate that time horizons make sense"""
        # Get recent predictions
        predictions = self.db.query(Prediction).filter(
            Prediction.symbol == self.symbol,
            Prediction.timeframe == self.timeframe
        ).order_by(Prediction.produced_at.desc()).limit(10).all()
        
        if not predictions:
            return {
                'status': 'WARNING',
                'message': 'No predictions found to validate',
                'recommendations': ['Generate predictions first']
            }
        
        issues = []
        horizon_minutes_list = []
        
        for pred in predictions:
            horizon_minutes_list.append(pred.horizon_minutes)
            
            # Check if predicted series length matches horizon
            if pred.predicted_series:
                series_length = len(pred.predicted_series)
                timeframe_mins = self._timeframe_to_minutes(self.timeframe)
                expected_points = pred.horizon_minutes / timeframe_mins
                
                if abs(series_length - expected_points) > 2:  # Allow small tolerance
                    issues.append(
                        f"Prediction has {series_length} points but horizon is "
                        f"{pred.horizon_minutes}min ({expected_points:.1f} expected points)"
                    )
        
        # Check for consistent horizons
        unique_horizons = set(horizon_minutes_list)
        if len(unique_horizons) > 1:
            issues.append(f"Inconsistent horizons found: {unique_horizons}")
        
        status = 'OK' if not issues else 'WARNING'
        
        return {
            'status': status,
            'horizon_minutes': horizon_minutes_list[0] if horizon_minutes_list else None,
            'horizon_hours': horizon_minutes_list[0] / 60 if horizon_minutes_list else None,
            'issues': issues,
            'recommendations': self._get_horizon_recommendations(issues)
        }
    
    def analyze_return_distribution(self) -> Dict:
        """Analyze actual vs predicted return distributions"""
        # Get historical candles
        candles = self.db.query(Candle).filter(
            Candle.symbol == self.symbol,
            Candle.timeframe == self.timeframe
        ).order_by(Candle.start_ts).all()
        
        if len(candles) < 100:
            return {
                'status': 'WARNING',
                'message': 'Insufficient data for return analysis',
                'recommendations': ['Need at least 100 candles']
            }
        
        df = pd.DataFrame([{
            'start_ts': c.start_ts,
            'close': c.close
        } for c in candles])
        
        # Calculate various horizon returns
        horizons = {
            '1_candle': 1,
            '4_hours': int(240 / self._timeframe_to_minutes(self.timeframe)),
            '1_day': int(1440 / self._timeframe_to_minutes(self.timeframe)),
        }
        
        return_stats = {}
        for name, shift in horizons.items():
            if shift < len(df):
                df[f'return_{name}'] = (df['close'].shift(-shift) / df['close'] - 1) * 100
                returns = df[f'return_{name}'].dropna()
                
                return_stats[name] = {
                    'mean': float(returns.mean()),
                    'std': float(returns.std()),
                    'min': float(returns.min()),
                    'max': float(returns.max()),
                    'q01': float(returns.quantile(0.01)),
                    'q99': float(returns.quantile(0.99)),
                    'median': float(returns.median())
                }
        
        # Check for unrealistic values
        issues = []
        for name, stats in return_stats.items():
            if abs(stats['max']) > 50:  # 50% move is very rare
                issues.append(f"{name}: Extreme max return {stats['max']:.2f}%")
            if abs(stats['min']) > 50:
                issues.append(f"{name}: Extreme min return {stats['min']:.2f}%")
        
        status = 'OK' if not issues else 'WARNING'
        
        return {
            'status': status,
            'return_stats': return_stats,
            'issues': issues,
            'recommendations': self._get_return_recommendations(return_stats, issues)
        }
    
    def check_prediction_sanity(self) -> Dict:
        """Check if predictions are realistic"""
        predictions = self.db.query(Prediction).filter(
            Prediction.symbol == self.symbol,
            Prediction.timeframe == self.timeframe
        ).order_by(Prediction.produced_at.desc()).limit(50).all()
        
        if not predictions:
            return {
                'status': 'WARNING',
                'message': 'No predictions to check',
                'recommendations': ['Generate predictions first']
            }
        
        # Get current price
        latest_candle = self.db.query(Candle).filter(
            Candle.symbol == self.symbol,
            Candle.timeframe == self.timeframe
        ).order_by(Candle.start_ts.desc()).first()
        
        if not latest_candle:
            return {'status': 'ERROR', 'message': 'No candle data'}
        
        current_price = latest_candle.close
        
        # Analyze predictions
        extreme_predictions = []
        prediction_returns = []
        
        for pred in predictions:
            if pred.predicted_series and len(pred.predicted_series) > 0:
                first_pred = pred.predicted_series[0]['close']
                last_pred = pred.predicted_series[-1]['close']
                
                # Calculate implied returns
                first_return = (first_pred / current_price - 1) * 100
                total_return = (last_pred / current_price - 1) * 100
                
                prediction_returns.append(total_return)
                
                # Check for extreme predictions
                if abs(first_return) > 10:  # 10% in first step is extreme
                    extreme_predictions.append({
                        'type': 'first_step',
                        'return_pct': first_return,
                        'horizon_minutes': pred.horizon_minutes
                    })
                
                if abs(total_return) > 50:  # 50% total is very extreme
                    extreme_predictions.append({
                        'type': 'total',
                        'return_pct': total_return,
                        'horizon_minutes': pred.horizon_minutes,
                        'horizon_hours': pred.horizon_minutes / 60
                    })
        
        # Calculate prediction statistics
        if prediction_returns:
            pred_stats = {
                'mean': np.mean(prediction_returns),
                'std': np.std(prediction_returns),
                'min': np.min(prediction_returns),
                'max': np.max(prediction_returns)
            }
        else:
            pred_stats = {}
        
        status = 'OK'
        if len(extreme_predictions) > len(predictions) * 0.1:  # >10% extreme
            status = 'CRITICAL'
        elif extreme_predictions:
            status = 'WARNING'
        
        return {
            'status': status,
            'total_predictions_checked': len(predictions),
            'extreme_predictions': extreme_predictions,
            'prediction_stats': pred_stats,
            'recommendations': self._get_prediction_recommendations(extreme_predictions, pred_stats)
        }
    
    def detect_feature_leakage(self) -> Dict:
        """Detect potential feature leakage"""
        # This is a simplified check - in production you'd need to inspect
        # actual features used during training
        
        # Check if predictions are suspiciously accurate
        predictions = self.db.query(Prediction).filter(
            Prediction.symbol == self.symbol,
            Prediction.timeframe == self.timeframe
        ).order_by(Prediction.produced_at.desc()).limit(20).all()
        
        if not predictions:
            return {
                'status': 'UNKNOWN',
                'message': 'No predictions to check for leakage',
                'recommendations': []
            }
        
        # Check confidence levels
        high_confidence_count = sum(1 for p in predictions if p.confidence and p.confidence > 0.95)
        
        issues = []
        if high_confidence_count > len(predictions) * 0.5:
            issues.append(
                f"{high_confidence_count}/{len(predictions)} predictions have >95% confidence "
                "(possible leakage or overconfidence)"
            )
        
        status = 'OK' if not issues else 'WARNING'
        
        return {
            'status': status,
            'high_confidence_ratio': high_confidence_count / len(predictions) if predictions else 0,
            'issues': issues,
            'recommendations': [
                'Verify no future data is used in features',
                'Check that all features use only past/current data',
                'Implement walk-forward validation',
                'Use permutation tests to verify model learns real patterns'
            ]
        }
    
    def analyze_regime_coverage(self) -> Dict:
        """Check if data covers different market regimes"""
        candles = self.db.query(Candle).filter(
            Candle.symbol == self.symbol,
            Candle.timeframe == self.timeframe
        ).order_by(Candle.start_ts).all()
        
        if len(candles) < 100:
            return {
                'status': 'WARNING',
                'message': 'Insufficient data for regime analysis',
                'recommendations': ['Need more historical data']
            }
        
        df = pd.DataFrame([{
            'start_ts': c.start_ts,
            'close': c.close,
            'volume': c.volume
        } for c in candles])
        
        # Calculate rolling volatility (20-period)
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(20).std() * 100
        
        # Classify regimes
        vol_median = df['volatility'].median()
        df['regime'] = df['volatility'].apply(
            lambda x: 'high_vol' if x > vol_median * 1.5 else 'low_vol' if x < vol_median * 0.5 else 'normal'
        )
        
        regime_counts = df['regime'].value_counts().to_dict()
        
        # Check coverage
        issues = []
        for regime in ['high_vol', 'normal', 'low_vol']:
            count = regime_counts.get(regime, 0)
            pct = (count / len(df)) * 100 if len(df) > 0 else 0
            if pct < 10:
                issues.append(f"Low coverage of {regime} regime: {pct:.1f}%")
        
        status = 'OK' if not issues else 'WARNING'
        
        return {
            'status': status,
            'regime_distribution': regime_counts,
            'volatility_stats': {
                'mean': float(df['volatility'].mean()),
                'median': float(df['volatility'].median()),
                'min': float(df['volatility'].min()),
                'max': float(df['volatility'].max())
            },
            'issues': issues,
            'recommendations': self._get_regime_recommendations(issues)
        }
    
    # Helper methods
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """Convert timeframe string to minutes"""
        mapping = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }
        return mapping.get(timeframe, 5)
    
    def _print_results(self, results: Dict):
        """Pretty print results"""
        status = results.get('status', 'UNKNOWN')
        status_emoji = {
            'OK': '✅',
            'WARNING': '⚠️',
            'CRITICAL': '🔴',
            'ERROR': '❌',
            'UNKNOWN': '❓'
        }
        
        print(f"{status_emoji.get(status, '❓')} Status: {status}")
        
        for key, value in results.items():
            if key in ['status', 'recommendations', 'issues']:
                continue
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    if isinstance(v, float):
                        print(f"    {k}: {v:.4f}")
                    else:
                        print(f"    {k}: {v}")
            elif isinstance(value, (int, float)):
                if isinstance(value, float):
                    print(f"  {key}: {value:.4f}")
                else:
                    print(f"  {key}: {value}")
            else:
                print(f"  {key}: {value}")
        
        if results.get('issues'):
            print(f"\n  ⚠️  Issues:")
            for issue in results['issues']:
                print(f"    - {issue}")
        
        if results.get('recommendations'):
            print(f"\n  💡 Recommendations:")
            for rec in results['recommendations']:
                print(f"    - {rec}")
    
    def _print_overall_assessment(self, results: Dict):
        """Print overall assessment"""
        critical_count = sum(1 for r in results.values() if r.get('status') == 'CRITICAL')
        warning_count = sum(1 for r in results.values() if r.get('status') == 'WARNING')
        ok_count = sum(1 for r in results.values() if r.get('status') == 'OK')
        
        print(f"\n📊 Summary:")
        print(f"  ✅ OK: {ok_count}")
        print(f"  ⚠️  Warnings: {warning_count}")
        print(f"  🔴 Critical: {critical_count}")
        
        if critical_count > 0:
            print(f"\n🔴 CRITICAL ISSUES FOUND - DO NOT TRUST MODEL PREDICTIONS")
            print("   Fix critical issues before using this model in production!")
        elif warning_count > 2:
            print(f"\n⚠️  MULTIPLE WARNINGS - USE CAUTION")
            print("   Review warnings and validate model carefully")
        else:
            print(f"\n✅ Model appears reasonable, but always validate on out-of-sample data")
    
    def _get_data_volume_recommendations(self, actual: int, recommended: int) -> List[str]:
        """Get recommendations based on data volume"""
        recs = []
        if actual < recommended * 0.3:
            recs.append("CRITICAL: Fetch at least 90 days of historical data")
            recs.append("Current data is insufficient for reliable training")
        elif actual < recommended * 0.7:
            recs.append("Fetch more historical data (aim for 90+ days)")
            recs.append("Consider using longer timeframes if data is limited")
        else:
            recs.append("Data volume is adequate")
        return recs
    
    def _get_horizon_recommendations(self, issues: List[str]) -> List[str]:
        """Get recommendations based on horizon issues"""
        if not issues:
            return ["Time horizon appears correctly configured"]
        return [
            "Verify prediction horizon matches your trading strategy",
            "Check that predicted_series length = horizon_minutes / timeframe_minutes",
            "Review model training code to ensure labels match intended horizon"
        ]
    
    def _get_return_recommendations(self, stats: Dict, issues: List[str]) -> List[str]:
        """Get recommendations based on return distribution"""
        recs = []
        if issues:
            recs.append("Extreme returns detected - check for data errors or outliers")
            recs.append("Consider capping extreme values or using robust scaling")
        
        # Check if any horizon has reasonable returns
        for name, stat in stats.items():
            if abs(stat['max']) < 20 and abs(stat['min']) < 20:
                recs.append(f"{name} returns look reasonable ({stat['min']:.2f}% to {stat['max']:.2f}%)")
        
        return recs or ["Return distribution appears reasonable"]
    
    def _get_prediction_recommendations(self, extreme_preds: List[Dict], stats: Dict) -> List[str]:
        """Get recommendations based on prediction sanity"""
        recs = []
        if extreme_preds:
            recs.append("CRITICAL: Model generating unrealistic predictions!")
            recs.append("Possible causes:")
            recs.append("  1. Time horizon mismatch (predicting wrong timeframe)")
            recs.append("  2. Feature leakage (using future data)")
            recs.append("  3. Model overfitting to outliers")
            recs.append("  4. Data preprocessing error (wrong scaling)")
            recs.append("Actions:")
            recs.append("  - Verify label computation (check shift/lag logic)")
            recs.append("  - Check feature engineering for leakage")
            recs.append("  - Retrain with proper validation")
            recs.append("  - Add prediction sanity checks/clipping")
        else:
            recs.append("Predictions appear within reasonable ranges")
        return recs
    
    def _get_regime_recommendations(self, issues: List[str]) -> List[str]:
        """Get recommendations based on regime coverage"""
        if issues:
            return [
                "Limited regime coverage detected",
                "Model may not generalize to different market conditions",
                "Fetch more historical data covering various market regimes",
                "Consider training separate models for different regimes"
            ]
        return ["Good coverage of different market regimes"]


def main():
    """Run diagnostics for a specific symbol/timeframe"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Model & Data Diagnostics')
    parser.add_argument('--symbol', default='INFY.NS', help='Stock symbol')
    parser.add_argument('--timeframe', default='15m', help='Timeframe')
    
    args = parser.parse_args()
    
    diagnostics = ModelDiagnostics(args.symbol, args.timeframe)
    results = diagnostics.run_full_diagnostics()
    
    print("\n" + "="*80)
    print("✅ Diagnostics complete!")
    print("="*80)


if __name__ == "__main__":
    main()

