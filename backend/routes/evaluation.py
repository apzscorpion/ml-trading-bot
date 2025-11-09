"""
Evaluation and metrics endpoints.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict
import numpy as np
from datetime import datetime, timedelta

from backend.database import get_db, Prediction, PredictionEvaluation, Candle
from backend.utils.metrics import record_prediction_quality

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


def calculate_metrics(predicted: list, actual: list) -> Dict:
    """
    Calculate prediction accuracy metrics.
    
    Args:
        predicted: List of predicted prices
        actual: List of actual prices
    
    Returns:
        Dictionary with RMSE, MAE, MAPE, directional accuracy
    """
    if not predicted or not actual or len(predicted) != len(actual):
        return {}
    
    pred_array = np.array(predicted)
    actual_array = np.array(actual)
    
    # RMSE (Root Mean Square Error)
    rmse = np.sqrt(np.mean((pred_array - actual_array) ** 2))
    
    # MAE (Mean Absolute Error)
    mae = np.mean(np.abs(pred_array - actual_array))
    
    # MAPE (Mean Absolute Percentage Error)
    mape = np.mean(np.abs((actual_array - pred_array) / actual_array)) * 100
    
    # Directional Accuracy
    if len(predicted) > 1:
        pred_direction = np.diff(pred_array) > 0
        actual_direction = np.diff(actual_array) > 0
        directional_accuracy = np.mean(pred_direction == actual_direction) * 100
    else:
        directional_accuracy = 0.0
    
    return {
        "rmse": float(rmse),
        "mae": float(mae),
        "mape": float(mape),
        "directional_accuracy": float(directional_accuracy),
        "n_samples": len(predicted)
    }


@router.post("/evaluate/{prediction_id}")
async def evaluate_prediction(
    prediction_id: int,
    db: Session = Depends(get_db)
):
    """
    Evaluate a prediction against actual data.
    """
    # Get prediction
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    
    if not prediction:
        return {"error": "Prediction not found"}
    
    # Get actual candles for the predicted time range
    predicted_series = prediction.predicted_series
    if not predicted_series:
        return {"error": "No predicted series"}
    
    # Extract timestamps and predicted prices
    predicted_prices = []
    actual_prices = []
    actual_series = []
    
    for point in predicted_series:
        ts = datetime.fromisoformat(point["ts"].replace('Z', '+00:00'))
        predicted_price = point["price"]
        
        # Find actual candle at this timestamp
        # Allow some tolerance (±timeframe interval)
        tolerance = timedelta(minutes=10)
        actual_candle = db.query(Candle).filter(
            Candle.symbol == prediction.symbol,
            Candle.timeframe == prediction.timeframe,
            Candle.start_ts >= ts - tolerance,
            Candle.start_ts <= ts + tolerance
        ).first()
        
        if actual_candle:
            predicted_prices.append(predicted_price)
            actual_prices.append(actual_candle.close)
            actual_series.append({
                "ts": actual_candle.start_ts.isoformat(),
                "price": float(actual_candle.close)
            })
    
    if not actual_prices:
        return {"error": "No actual data available yet for evaluation"}
    
    # Calculate metrics
    metrics = calculate_metrics(predicted_prices, actual_prices)
    
    # Store evaluation - populate all required fields
    evaluation = PredictionEvaluation(
        prediction_id=prediction.id,
        symbol=prediction.symbol,
        timeframe=prediction.timeframe,
        evaluated_at=datetime.utcnow(),
        rmse=metrics.get("rmse"),
        mae=metrics.get("mae"),
        mape=metrics.get("mape"),
        directional_accuracy=metrics.get("directional_accuracy")
    )
    
    db.add(evaluation)
    db.commit()

    record_prediction_quality(
        symbol=prediction.symbol,
        timeframe=prediction.timeframe,
        metrics={
            'mae': metrics.get('mae', 0.0),
            'mape': metrics.get('mape', 0.0),
            'directional_accuracy': metrics.get('directional_accuracy', 0.0),
        }
    )
    
    return {
        "prediction_id": prediction.id,
        "evaluation_id": evaluation.id,
        "metrics": metrics,
        "actual_series": actual_series
    }


@router.get("/bot-performance")
async def get_bot_performance(
    symbol: str = Query(None, description="Filter by symbol"),
    days: int = Query(7, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get performance metrics for each bot.
    """
    # Get recent predictions with evaluations
    since = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(Prediction).join(PredictionEvaluation).filter(
        Prediction.produced_at >= since
    )
    
    if symbol:
        query = query.filter(Prediction.symbol == symbol)
    
    predictions = query.all()
    
    if not predictions:
        return {"message": "No evaluated predictions in this period"}
    
    # Aggregate metrics by bot
    bot_metrics = {}
    
    for pred in predictions:
        if not pred.evaluations:
            continue
        
        eval_data = pred.evaluations[0]  # Get first evaluation
        contributions = pred.bot_contributions or {}
        
        for bot_name, bot_data in contributions.items():
            if bot_name not in bot_metrics:
                bot_metrics[bot_name] = {
                    "predictions_count": 0,
                    "avg_confidence": 0,
                    "total_weight": 0,
                    "rmse_list": [],
                    "mae_list": [],
                    "directional_accuracy_list": []
                }
            
            bot_metrics[bot_name]["predictions_count"] += 1
            bot_metrics[bot_name]["avg_confidence"] += bot_data.get("confidence", 0)
            bot_metrics[bot_name]["total_weight"] += bot_data.get("weight", 0)
            
            if eval_data.metrics:
                bot_metrics[bot_name]["rmse_list"].append(eval_data.metrics.get("rmse", 0))
                bot_metrics[bot_name]["mae_list"].append(eval_data.metrics.get("mae", 0))
                bot_metrics[bot_name]["directional_accuracy_list"].append(
                    eval_data.metrics.get("directional_accuracy", 0)
                )
    
    # Calculate averages
    for bot_name in bot_metrics:
        count = bot_metrics[bot_name]["predictions_count"]
        if count > 0:
            bot_metrics[bot_name]["avg_confidence"] /= count
            bot_metrics[bot_name]["avg_weight"] = bot_metrics[bot_name]["total_weight"] / count
            
            if bot_metrics[bot_name]["rmse_list"]:
                bot_metrics[bot_name]["avg_rmse"] = np.mean(bot_metrics[bot_name]["rmse_list"])
                bot_metrics[bot_name]["avg_mae"] = np.mean(bot_metrics[bot_name]["mae_list"])
                bot_metrics[bot_name]["avg_directional_accuracy"] = np.mean(
                    bot_metrics[bot_name]["directional_accuracy_list"]
                )
            
            # Clean up lists
            del bot_metrics[bot_name]["rmse_list"]
            del bot_metrics[bot_name]["mae_list"]
            del bot_metrics[bot_name]["directional_accuracy_list"]
            del bot_metrics[bot_name]["total_weight"]
    
    return {
        "period_days": days,
        "symbol": symbol,
        "bot_performance": bot_metrics
    }


@router.get("/metrics/summary")
async def get_metrics_summary(
    symbol: str = Query(..., description="Stock symbol"),
    timeframe: str = Query("5m", description="Timeframe"),
    db: Session = Depends(get_db)
):
    """Get summary of prediction accuracy"""
    # Query directly from PredictionEvaluation - it already has symbol and timeframe
    try:
        evaluations = db.query(PredictionEvaluation).filter(
            PredictionEvaluation.symbol == symbol,
            PredictionEvaluation.timeframe == timeframe
        ).order_by(PredictionEvaluation.evaluated_at.desc()).limit(20).all()
    except Exception as e:
        # If query fails due to missing columns, run migration and inform user
        error_str = str(e).lower()
        if "no such column" in error_str or "rmse" in error_str or "mae" in error_str:
            # Run migration to add missing columns
            try:
                from backend.migrate_db import migrate_database
                migrate_database()
                
                # Return error message asking user to retry after restart
                return {
                    "error": "Database schema mismatch detected",
                    "message": "The database schema was updated. Please refresh the page or restart the backend server.",
                    "original_error": str(e),
                    "hint": "The migration has been applied, but the connection pool needs to be refreshed. Restart the backend server."
                }
            except Exception as migration_error:
                return {
                    "error": "Database schema issue",
                    "message": f"Failed to migrate database: {str(migration_error)}",
                    "original_error": str(e),
                    "hint": "Please restart the backend server to apply database migrations"
                }
        else:
            raise
    
    if not evaluations:
        return {"message": "No evaluations available"}
    
    # Extract metrics from evaluation records
    # Handle both old schema (metrics JSON) and new schema (individual columns)
    all_rmse = []
    all_mae = []
    all_mape = []
    all_dir_acc = []
    
    for e in evaluations:
        # Try new schema first (individual columns)
        if hasattr(e, 'rmse') and e.rmse is not None:
            all_rmse.append(e.rmse)
        if hasattr(e, 'mae') and e.mae is not None:
            all_mae.append(e.mae)
        if hasattr(e, 'mape') and e.mape is not None:
            all_mape.append(e.mape)
        if hasattr(e, 'directional_accuracy') and e.directional_accuracy is not None:
            all_dir_acc.append(e.directional_accuracy)
        
        # Fallback to old schema (metrics JSON) if available
        if hasattr(e, 'metrics') and e.metrics and isinstance(e.metrics, dict):
            if not all_rmse and 'rmse' in e.metrics:
                all_rmse.append(e.metrics.get('rmse'))
            if not all_mae and 'mae' in e.metrics:
                all_mae.append(e.metrics.get('mae'))
            if not all_mape and 'mape' in e.metrics:
                all_mape.append(e.metrics.get('mape'))
            if not all_dir_acc and 'directional_accuracy' in e.metrics:
                all_dir_acc.append(e.metrics.get('directional_accuracy'))
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "evaluations_count": len(evaluations),
        "avg_rmse": float(np.mean(all_rmse)) if all_rmse else 0,
        "avg_mae": float(np.mean(all_mae)) if all_mae else 0,
        "avg_mape": float(np.mean(all_mape)) if all_mape else 0,
        "avg_directional_accuracy": float(np.mean(all_dir_acc)) if all_dir_acc else 0
    }

