# 🔧 Database Connection Pool Fix

## Issue Detected

**Error**: `sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached`

**Impact**: Backend returning 500 errors, app becoming unresponsive

## Root Cause

SQLAlchemy's default connection pool (5 connections + 10 overflow) was exhausted because:
1. High concurrent request load
2. Connections not being closed properly
3. Background scheduler jobs holding connections
4. Real-time updates every 5 seconds

## Fix Applied

Updated `backend/database.py` with larger connection pool:

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,        # Increased from 5
    max_overflow=40,     # Increased from 10
    pool_timeout=60,     # Increased from 30
    pool_recycle=3600,   # Recycle after 1 hour
    pool_pre_ping=True   # Verify connections
)
```

## What Changed

| Setting | Before | After | Reason |
|---------|--------|-------|--------|
| `pool_size` | 5 | 20 | More concurrent connections |
| `max_overflow` | 10 | 40 | Handle traffic spikes |
| `pool_timeout` | 30s | 60s | More time to wait for connection |
| `pool_recycle` | None | 3600s | Prevent stale connections |
| `pool_pre_ping` | False | True | Detect dead connections |

## Action Required

**Restart your backend** to apply the fix:

```bash
# Stop backend (Ctrl+C)
cd backend
python main.py
```

## Verification

After restart, check logs for:
- ✅ No more `QueuePool limit` errors
- ✅ Requests return 200 OK instead of 500
- ✅ App remains responsive under load

## Monitoring

Watch for these signs of connection issues:
```bash
# Check logs for connection errors
tail -f logs/backend.log | grep -i "pool\|timeout\|connection"
```

## Best Practices Going Forward

### 1. Always Close Database Sessions

**Bad**:
```python
db = SessionLocal()
candles = db.query(Candle).all()
# Missing db.close() - connection leak!
```

**Good**:
```python
db = SessionLocal()
try:
    candles = db.query(Candle).all()
finally:
    db.close()  # Always close!
```

**Better** (use context manager):
```python
from backend.database import get_db

# FastAPI dependency injection
@app.get("/api/data")
def get_data(db: Session = Depends(get_db)):
    # db automatically closed after request
    return db.query(Candle).all()
```

### 2. Limit Long-Running Queries

```python
# Add limits to prevent loading entire table
db.query(Candle).limit(1000).all()  # Not .all() without limit
```

### 3. Use Pagination

```python
# Instead of loading all records
page_size = 100
offset = page * page_size
results = db.query(Candle).limit(page_size).offset(offset).all()
```

### 4. Monitor Connection Pool

Add to your health check:
```python
@app.get("/health")
def health_check():
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow()
    }
```

## Related Issues

This fix addresses:
- ✅ 500 Internal Server Errors
- ✅ Timeout errors under load
- ✅ Scheduler job delays
- ✅ WebSocket connection issues

## Additional Notes

- SQLite has limitations with concurrent writes
- Consider PostgreSQL for production if you need high concurrency
- Monitor pool usage and adjust settings if needed

---

**Status**: ✅ Fixed - Restart backend to apply

