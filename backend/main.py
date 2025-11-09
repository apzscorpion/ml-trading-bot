"""
Main FastAPI application for trading prediction app.
Includes REST API, WebSocket support, and background scheduler.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from contextlib import asynccontextmanager
import logging
import json
import asyncio
import pytz
from typing import Dict, Set
from datetime import datetime, timedelta

from backend.database import init_db, SessionLocal, Candle
from backend.routes import history, prediction, evaluation, recommendation, debug, models, training, market, intraday, freddy, versioning
from backend.utils.data_fetcher import data_fetcher
from backend.freddy_merger import freddy_merger
from backend.config import settings
from backend.websocket_manager import manager
from backend.utils.metrics import record_prediction, update_websocket_connections, record_regime

# Configure structured logging
from backend.utils.logger import configure_logging, get_logger, get_request_id, set_request_id
configure_logging(settings.log_level)
logger = get_logger(__name__)

scheduler = AsyncIOScheduler()


def get_network_ip():
    """Get the local network IP address"""
    import socket
    try:
        # Create a socket to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "Unable to detect"


async def scheduled_data_fetch_and_predict():
    """
    Background task that runs every N minutes:
    1. Fetch latest candles
    2. Store in DB
    3. Generate predictions
    4. Broadcast updates
    """
    logger.info("Running scheduled data fetch and prediction...")
    
    db = SessionLocal()
    try:
        # Get default symbol and timeframe
        symbol = settings.default_symbol
        timeframe = settings.yahoo_finance_interval
        
        # Fetch latest candles
        # NOTE: Yahoo Finance requires at least 5d period for 5m intervals on Indian stocks
        try:
            period_map = {
                "1m": "7d",
                "5m": "5d",  # Changed from 1d to 5d - Yahoo Finance requirement
                "15m": "5d",
                "1h": "5d",
                "4h": "5d",
                "1d": "1mo"
            }
            period = period_map.get(timeframe, "5d")
            
            candles = await data_fetcher.fetch_candles(
                symbol=symbol,
                interval=timeframe,
                period=period
            )
            
            if not candles:
                logger.debug(f"No candles fetched for {symbol} (may be market closed or symbol unavailable)")
                return
        except Exception as e:
            logger.debug(f"Failed to fetch candles for {symbol}: {e}")
            return
        
        # Store in database
        for candle_data in candles[-10:]:  # Store last 10 candles
            # Convert start_ts from ISO string to datetime if needed
            candle_dict = candle_data.copy()
            if isinstance(candle_dict.get('start_ts'), str):
                candle_dict['start_ts'] = datetime.fromisoformat(
                    candle_dict['start_ts'].replace('Z', '+00:00')
                )
            
            # Check if exists (compare datetime objects)
            existing = db.query(Candle).filter(
                Candle.symbol == symbol,
                Candle.timeframe == timeframe,
                Candle.start_ts == candle_dict["start_ts"]
            ).first()
            
            if not existing:
                candle = Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    **candle_dict
                )
                db.add(candle)
        
        db.commit()
        
        # Broadcast latest candle
        if candles:
            await manager.broadcast_candle(symbol, timeframe, candles[-1])
        
        # Generate prediction
        request_id = get_request_id()
        logger.info(
            "generating_prediction",
            request_id=request_id,
            symbol=symbol,
            timeframe=timeframe,
            horizon_minutes=settings.default_horizon_minutes,
            candles_count=len(candles)
        )
        start_time = datetime.utcnow()
        
        prediction_result = await freddy_merger.predict(
            symbol=symbol,
            candles=candles,
            horizon_minutes=settings.default_horizon_minutes,
            timeframe=timeframe
        )
        
        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        try:
            regime = prediction_result.get("trend", {}).get("regime", "unknown")
            record_regime(symbol, timeframe, str(regime))
        except Exception as regime_error:  # pragma: no cover - non-critical metric
            logger.warning("Failed to record regime metric", error=str(regime_error))
        
        # Log prediction with full context
        feature_snapshot = {
            "last_candles": [candles[i] for i in range(max(0, len(candles)-5), len(candles))],
            "latest_price": candles[-1]["close"] if candles else None,
            "price_range": {
                "min": min(c.get("low", 0) for c in candles[-20:]) if len(candles) >= 20 else None,
                "max": max(c.get("high", 0) for c in candles[-20:]) if len(candles) >= 20 else None
            },
            "volume_avg": sum(c.get("volume", 0) for c in candles[-20:]) / min(20, len(candles)) if candles else None
        }
        
        logger.info(
            "prediction_generated",
            request_id=request_id,
            symbol=symbol,
            timeframe=timeframe,
            horizon_minutes=settings.default_horizon_minutes,
            prediction_count=len(prediction_result.get("predicted_series", [])),
            confidence=prediction_result.get("overall_confidence"),
            bot_contributions_count=len(prediction_result.get("bot_contributions", {})),
            latency_ms=round(latency_ms, 2),
            input_candles_count=len(candles),
            feature_snapshot=feature_snapshot,
            trend=prediction_result.get("trend", {}),
            model_version=prediction_result.get("model_version", "unknown")
        )
        
        # Store prediction
        from backend.database import Prediction
        prediction = Prediction(
            symbol=prediction_result["symbol"],
            produced_at=datetime.fromisoformat(
                prediction_result["produced_at"].replace('Z', '+00:00')
            ),
            horizon_minutes=prediction_result["horizon_minutes"],
            timeframe=prediction_result["timeframe"],
            predicted_series=prediction_result["predicted_series"],
            confidence=prediction_result["overall_confidence"],
            bot_contributions=prediction_result["bot_contributions"],
            trend=prediction_result.get("trend")
        )
        db.add(prediction)
        db.commit()
        
        # Broadcast prediction
        await manager.broadcast_prediction(prediction_result)
        
        # Record metrics
        record_prediction("freddy_merger", symbol, timeframe, latency_ms / 1000.0)
        update_websocket_connections(len(manager.active_connections))
        
        logger.info(f"Prediction generated and broadcast for {symbol}")
        
    except Exception as e:
        logger.error(
            "Error in scheduled data fetch and prediction task",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        db.rollback()
    finally:
        db.close()


# Rate limiting for API calls - track last fetch time per symbol/timeframe
_last_fetch_times: Dict[str, datetime] = {}
_MIN_FETCH_INTERVAL = timedelta(seconds=5)  # Minimum 5 seconds between API calls per symbol/timeframe

async def scheduled_realtime_candle_updates():
    """
    Real-time candle updates - runs every 1 second
    to broadcast live candle updates to all subscribed clients.
    This provides TradingView-like real-time updates with 1-second granularity.
    
    Uses rate limiting to prevent API overload - only fetches from API every 5 seconds,
    but broadcasts cached updates every second for smooth real-time feel.
    """
    db = SessionLocal()
    try:
        # Get all active subscriptions
        subscriptions = manager.get_all_subscriptions()
        
        if not subscriptions:
            return  # No active subscriptions
        
        # Fetch updates for each subscribed symbol/timeframe
        for subscription in subscriptions:
            symbol = subscription.get("symbol")
            timeframe = subscription.get("timeframe")
            
            if not symbol or not timeframe:
                continue
            
            try:
                # Rate limiting: check if we should fetch from API or use cache
                cache_key = f"{symbol}_{timeframe}"
                last_fetch = _last_fetch_times.get(cache_key)
                now = datetime.utcnow()
                
                should_fetch_from_api = False
                if last_fetch is None or (now - last_fetch) >= _MIN_FETCH_INTERVAL:
                    should_fetch_from_api = True
                    _last_fetch_times[cache_key] = now
                
                # Fetch latest candles (use cache if rate limited, otherwise bypass cache)
                candles = await data_fetcher.fetch_candles(
                    symbol=symbol,
                    interval=timeframe,
                    period="1d",
                    bypass_cache=should_fetch_from_api  # Only bypass cache if not rate limited
                )
                
                if not candles:
                    continue
                
                # Get the latest candle (which is currently forming)
                latest_candle = candles[-1]
                
                # Store in database if new
                candle_dict = latest_candle.copy()
                if isinstance(candle_dict.get('start_ts'), str):
                    candle_dict['start_ts'] = datetime.fromisoformat(
                        candle_dict['start_ts'].replace('Z', '+00:00')
                    )
                
                # Check if exists (compare datetime objects)
                existing = db.query(Candle).filter(
                    Candle.symbol == symbol,
                    Candle.timeframe == timeframe,
                    Candle.start_ts == candle_dict["start_ts"]
                ).first()
                
                if not existing:
                    candle = Candle(
                        symbol=symbol,
                        timeframe=timeframe,
                        **candle_dict
                    )
                    db.add(candle)
                    db.commit()
                else:
                    # Update existing candle (live update)
                    existing.open = candle_dict.get('open', existing.open)
                    existing.high = max(existing.high, candle_dict.get('high', existing.high))
                    existing.low = min(existing.low, candle_dict.get('low', existing.low))
                    existing.close = candle_dict.get('close', existing.close)
                    existing.volume = candle_dict.get('volume', existing.volume)
                    db.commit()
                
                # Broadcast candle update to subscribed clients
                await manager.broadcast_candle(symbol, timeframe, latest_candle)
                
            except Exception as e:
                logger.error(
                    "Error updating candle",
                    symbol=symbol,
                    timeframe=timeframe,
                    error=str(e),
                    error_type=type(e).__name__
                )
                continue
        
    except Exception as e:
        logger.error(
            "Error in real-time candle update task",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
    finally:
        db.close()


async def scheduled_auto_training():
    """
    Automatically trigger training for all models at scheduled times.
    Runs at 9:00 AM IST and 3:30 PM IST daily.
    """
    from backend.routes.training import training_state, process_training_queue
    
    logger.info("🔄 Scheduled auto-training triggered")
    
    # Check if training is already running
    if training_state["is_running"]:
        logger.warning("⚠️ Training already running, skipping scheduled training")
        return
    
    # Default configuration for scheduled training
    symbols = ["TCS.NS", "RELIANCE.NS", "AXISBANK.NS"]
    timeframes = ["5m", "15m", "1h", "1d"]
    bots = ["lstm_bot", "transformer_bot", "ml_bot", "ensemble_bot"]
    
    # Build training queue
    queue = []
    for symbol in symbols:
        for timeframe in timeframes:
            for bot_name in bots:
                queue.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "bot_name": bot_name,
                    "status": "pending"
                })
    
    # Set training state
    training_state["queue"] = queue
    training_state["is_running"] = True
    training_state["is_paused"] = False
    training_state["completed"] = []
    training_state["failed"] = []
    
    # Start processing queue in background
    asyncio.create_task(process_training_queue())
    
    logger.info(f"✅ Scheduled training started with {len(queue)} tasks")
    logger.info(f"   Symbols: {symbols}")
    logger.info(f"   Timeframes: {timeframes}")
    logger.info(f"   Bots: {bots}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    logger.info("Starting trading prediction app...")
    init_db()
    
    # Start scheduler
    scheduler.add_job(
        scheduled_data_fetch_and_predict,
        trigger=IntervalTrigger(seconds=settings.prediction_interval),
        id="data_fetch_and_predict",
        name="Fetch data and generate predictions",
        replace_existing=True
    )
    
    # Start real-time candle updates scheduler (runs every 5 seconds to avoid overload)
    scheduler.add_job(
        scheduled_realtime_candle_updates,
        trigger=IntervalTrigger(seconds=5),  # Update every 5 seconds to avoid scheduler overload
        id="realtime_candle_updates",
        name="Real-time candle updates",
        replace_existing=True,
        max_instances=1,  # Only allow one instance at a time
        coalesce=True  # Combine multiple pending executions into one
    )
    
    # Schedule automatic training at 9:00 AM IST daily
    ist = pytz.timezone('Asia/Kolkata')
    scheduler.add_job(
        scheduled_auto_training,
        trigger=CronTrigger(hour=9, minute=0, timezone=ist),
        id="auto_training_0900",
        name="Auto training at 9:00 AM IST",
        replace_existing=True
    )
    
    # Schedule automatic training at 3:30 PM IST daily
    scheduler.add_job(
        scheduled_auto_training,
        trigger=CronTrigger(hour=15, minute=30, timezone=ist),
        id="auto_training_1530",
        name="Auto training at 3:30 PM IST",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"Scheduler started. Data fetch runs every {settings.prediction_interval} seconds.")
    logger.info("✅ Real-time candle updates enabled (every 1 second)")
    logger.info("✅ Scheduled auto-training configured:")
    logger.info("   - 9:00 AM IST daily")
    logger.info("   - 3:30 PM IST daily")
    
    # Display network access information
    network_ip = get_network_ip()
    logger.info("")
    logger.info("=" * 70)
    logger.info("🌐 NETWORK ACCESS INFORMATION")
    logger.info("=" * 70)
    logger.info(f"📍 Local Access:   http://localhost:8182")
    logger.info(f"📍 Network Access: http://{network_ip}:8182")
    logger.info(f"📍 API Docs:       http://{network_ip}:8182/docs")
    logger.info(f"📍 Health Check:   http://{network_ip}:8182/health")
    logger.info(f"📍 WebSocket:      ws://{network_ip}:8182/ws")
    logger.info("")
    logger.info(f"📱 Access from other devices on your network:")
    logger.info(f"   Frontend: http://{network_ip}:5155")
    logger.info(f"   Backend:  http://{network_ip}:8182")
    logger.info("=" * 70)
    logger.info("")
    
    yield
    
    # Shutdown
    scheduler.shutdown()
    logger.info("Application shutdown")


# Create FastAPI app
app = FastAPI(
    title="Trading Prediction API",
    description="AI-powered stock prediction system with multiple bots",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
allowed_origins_list = settings.allowed_origins.split(",") if settings.allowed_origins else ["http://localhost:5155"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(history.router)
app.include_router(prediction.router)
app.include_router(evaluation.router)
app.include_router(recommendation.router)
app.include_router(debug.router)
app.include_router(models.router)
app.include_router(training.router)
app.include_router(market.router)
app.include_router(intraday.router)
app.include_router(freddy.router)
app.include_router(versioning.router)

# Market status router
from backend.routes import market_status
app.include_router(market_status.router)

# Backtest router
from backend.routes import backtest
app.include_router(backtest.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Trading Prediction API",
        "version": "1.0.0",
        "status": "running",
        "websocket": "/ws",
        "docs": "/docs",
        "metrics": "/metrics"
    }


from backend.utils.metrics import get_metrics

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=get_metrics(), media_type="text/plain")

@app.get("/health")
async def health_check():
    """Health check endpoint with component-level status checks"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_connections": len(manager.active_connections),
        "scheduler_running": scheduler.running,
        "components": {}
    }
    
    # Check database
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db.close()
        health_status["components"]["database"] = "healthy"
    except Exception as e:
        health_status["components"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check data fetcher
    try:
        test_data = await data_fetcher.fetch_candles("TCS.NS", "5m", "1d", bypass_cache=True)
        if test_data:
            health_status["components"]["data_fetcher"] = "healthy"
            cache_stats = data_fetcher.get_cache_stats()
            health_status["components"]["cache"] = cache_stats
        else:
            health_status["components"]["data_fetcher"] = "degraded: no data returned"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["components"]["data_fetcher"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis cache
    from backend.utils.redis_cache import redis_cache
    redis_status = redis_cache.get_stats()
    health_status["components"]["redis"] = redis_status
    
    # Check model availability
    from backend.freddy_merger import freddy_merger
    model_status = {}
    for bot in freddy_merger.bots:
        if hasattr(bot, "model"):
            model_status[bot.name] = "available" if bot.model is not None else "not_loaded"
        elif hasattr(bot, "models"):
            model_status[bot.name] = "available" if bot.models else "not_loaded"
        else:
            model_status[bot.name] = "n/a"
    
    health_status["components"]["models"] = model_status
    
    # Check exchange calendar and market status
    from backend.utils.exchange_calendar import exchange_calendar
    import pytz
    ist = pytz.timezone('Asia/Kolkata')
    current_ist = datetime.now(ist)
    market_status = exchange_calendar.validate_trading_session(current_ist)
    health_status["components"]["exchange_calendar"] = {
        "status": "healthy",
        "market_status": market_status
    }
    
    return health_status


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    Client messages:
    - {"action": "subscribe", "symbol": "TCS.NS", "timeframe": "5m"}
    - {"action": "unsubscribe"}
    
    Server messages:
    - {"type": "candle:update", "symbol": "...", "candle": {...}}
    - {"type": "prediction:update", "symbol": "...", "predicted_series": [...]}
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            action = message.get("action")
            
            if action == "subscribe":
                symbol = message.get("symbol", settings.default_symbol)
                timeframe = message.get("timeframe", settings.yahoo_finance_interval)
                manager.subscribe(websocket, symbol, timeframe)
                
                # Send confirmation
                await websocket.send_json({
                    "type": "subscribed",
                    "symbol": symbol,
                    "timeframe": timeframe
                })
            
            elif action == "unsubscribe":
                if websocket in manager.subscriptions:
                    del manager.subscriptions[websocket]
                await websocket.send_json({"type": "unsubscribed"})
            
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    
    # Display startup banner
    network_ip = get_network_ip()
    print("\n" + "=" * 70)
    print("🚀 Starting Trading Prediction API")
    print("=" * 70)
    print(f"📍 Local Access:   http://localhost:8182")
    print(f"📍 Network Access: http://{network_ip}:8182")
    print(f"📍 API Docs:       http://{network_ip}:8182/docs")
    print(f"📍 Health Check:   http://{network_ip}:8182/health")
    print("")
    print(f"📱 Access from other devices:")
    print(f"   Frontend: http://{network_ip}:5155")
    print(f"   Backend:  http://{network_ip}:8182")
    print("=" * 70 + "\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8182,
        reload=True,
        log_level="info"
    )

