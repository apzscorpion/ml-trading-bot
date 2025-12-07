import pytest
import asyncio
import sys
from unittest.mock import MagicMock, patch, AsyncMock

from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from backend.database import Prediction, PredictionEvaluation, Candle, Base
from backend.services.prediction_evaluator import prediction_evaluator
from backend.ml.ai_training_orchestrator import ai_training_orchestrator, AITrainingDataPoint

# Mock data fetcher
@pytest.fixture
def mock_data_fetcher():
    with patch('backend.services.prediction_evaluator.data_fetcher') as mock:
        yield mock

@pytest.fixture
def mock_db_session():
    with patch('backend.services.prediction_evaluator.SessionLocal') as mock:
        session = MagicMock()
        mock.return_value = session
        yield session

@pytest.mark.asyncio
async def test_feedback_loop_flow(mock_data_fetcher, mock_db_session):
    # 1. Setup: Create a past prediction
    now = datetime.utcnow()
    past_time = now - timedelta(hours=2)
    
    prediction = Prediction(
        id=1,
        symbol="INFY",
        timeframe="5m",
        produced_at=past_time,
        horizon_minutes=60,
        prediction_type="ensemble",
        predicted_series=[
            {"ts": (past_time + timedelta(minutes=15)).isoformat(), "price": 100.0},
            {"ts": (past_time + timedelta(minutes=30)).isoformat(), "price": 101.0},
            {"ts": (past_time + timedelta(minutes=45)).isoformat(), "price": 102.0},
            {"ts": (past_time + timedelta(minutes=60)).isoformat(), "price": 103.0},
        ]
    )
    
    # Mock DB query
    # Make filter() return the same query object to handle chaining of any depth
    mock_query = mock_db_session.query.return_value
    mock_query.filter.return_value = mock_query
    
    # Mock check for existing evaluations (return empty)
    # First call: evaluated_ids (should be empty)
    # Second call: pending_predictions (should return our prediction)
    mock_query.all.side_effect = [[], [prediction]] 

    # 2. Setup: Mock "Actual" data that contradicts prediction (Price went DOWN instead of UP)
    # Predicted: 100 -> 103
    # Actual: 100 -> 95
    actual_candles = [
        {'start_ts': (past_time + timedelta(minutes=15)).isoformat(), 'close': 100.0},
        {'start_ts': (past_time + timedelta(minutes=30)).isoformat(), 'close': 98.0},
        {'start_ts': (past_time + timedelta(minutes=45)).isoformat(), 'close': 96.0},
        {'start_ts': (past_time + timedelta(minutes=60)).isoformat(), 'close': 95.0},
    ]
    # Configure fetch_candles as AsyncMock
    mock_data_fetcher.fetch_candles = AsyncMock(return_value=actual_candles)
    
    # 3. Run Evaluation
    await prediction_evaluator.evaluate_pending_predictions(lookback_hours=4)
    
    # 4. Verify Evaluation
    # Check if db.add was called with a PredictionEvaluation
    args = mock_db_session.add.call_args
    assert args is not None
    evaluation = args[0][0]
    
    assert isinstance(evaluation, PredictionEvaluation)
    assert evaluation.prediction_id == 1
    assert evaluation.symbol == "INFY"
    # RMSE should be significant
    # Pred: 100, 101, 102, 103
    # Act:  100, 98, 96, 95
    # Diff: 0, 3, 6, 8
    # RMSE approx sqrt((0+9+36+64)/4) = sqrt(27.25) = ~5.2
    assert evaluation.rmse > 4.0
    assert evaluation.directional_accuracy == 0.0 # Pred UP, Act DOWN
    
    print(f"Calculated RMSE: {evaluation.rmse}")
    print(f"Calculated MAPE: {evaluation.mape}")
    
    # 5. Test Dataset Generation from Mistakes
    # Now we need to mock the DB for the orchestrator part
    
    # Mock finding the mistake
    mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [evaluation]
    
    # Mock finding the original prediction
    mock_db_session.query.return_value.filter.return_value.first.return_value = prediction
    
    # Mock finding historical candles (context)
    # Need at least 50 candles to pass the check
    context_candles = [
        MagicMock(
            start_ts=past_time - timedelta(minutes=5*i), 
            close=100.0, 
            to_dict=lambda: {
                'start_ts': (past_time - timedelta(minutes=5*i)).isoformat(),
                'open': 100.0, 
                'high': 101.0, 
                'low': 99.0, 
                'close': 100.0, 
                'volume': 1000
            }
        )
        for i in range(50)
    ]
    # Mock finding actual outcome candle
    outcome_candle = MagicMock(close=95.0) # The actual price at horizon
    
    # We need to be careful with the chaining of mocks for the orchestrator queries
    # It queries: PredictionEvaluation, then Prediction, then Candle (context), then Candle (outcome)
    
    # Let's patch the orchestrator method's internal DB calls or just rely on the complex mock chain
    # Simpler: Patch SessionLocal in orchestrator
    with patch('backend.ml.ai_training_orchestrator.SessionLocal') as mock_orch_session_cls:
        mock_orch_session = MagicMock()
        mock_orch_session_cls.return_value = mock_orch_session
        
        # Setup queries
        # 1. Query mistakes
        mock_orch_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [evaluation]
        
        # 2. Query prediction (by id)
        # We need side_effect to return different things for different queries if possible
        # Or just ensure the first query returns prediction
        
        # This is getting complex to mock perfectly with chained queries. 
        # Let's assume the logic works if the unit test above passed, and focus on the logic inside generate_dataset_from_mistakes
        # by calling it with mocked DB results.
        
        # Actually, let's just verify the logic of generate_dataset_from_mistakes by mocking the DB returns in sequence
        def query_side_effect(model):
            query_mock = MagicMock()
            if model == PredictionEvaluation:
                query_mock.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [evaluation]
            elif model == Prediction:
                query_mock.filter.return_value.first.return_value = prediction
            elif model == Candle:
                # This is tricky because it's called twice with different filters
                # We'll return a mock that returns context first, then outcome
                # But filter() returns a query object, not results directly.
                # Let's just return a generic mock that returns what we need
                query_mock.filter.return_value.order_by.return_value.all.return_value = context_candles
                query_mock.filter.return_value.order_by.return_value.first.return_value = outcome_candle
            return query_mock
            
        mock_orch_session.query.side_effect = query_side_effect
        
        # Run generation
        training_points, metadata = await ai_training_orchestrator.generate_dataset_from_mistakes(min_error_threshold=1.0)
        
        assert len(training_points) == 1
        point = training_points[0]
        
        # Verify the target is the ACTUAL price (95.0), not the predicted one
        assert point.target_price == 95.0
        assert point.timestamp == prediction.produced_at
        
        print("Successfully generated correction point with actual target price")

if __name__ == "__main__":
    # Manually run the async test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_feedback_loop_flow(MagicMock(), MagicMock()))
