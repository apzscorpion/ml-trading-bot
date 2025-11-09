# ✅ Fixed: BaseBot.__init__() Missing Required Argument Error

## Error Fixed

```
TypeError: BaseBot.__init__() missing 1 required positional argument: 'name'
```

## Root Cause

Several bot classes were calling `super().__init__(self.name)` where `self.name` is a class variable. While this should work in most cases, Python's method resolution order (MRO) can sometimes cause issues when accessing class variables via `self` before the parent `__init__` has been called.

## Solution

Changed all bots from using `self.name` to using string literals directly in `super().__init__()`:

**Before:**
```python
def __init__(self):
    super().__init__(self.name)  # ❌ Can fail if self.name not accessible yet
```

**After:**
```python
def __init__(self):
    super().__init__("bot_name")  # ✅ String literal always works
```

## Files Fixed

1. ✅ `backend/bots/lstm_bot.py` - Changed `super().__init__(self.name)` → `super().__init__("lstm_bot")`
2. ✅ `backend/bots/transformer_bot.py` - Changed `super().__init__(self.name)` → `super().__init__("transformer_bot")`
3. ✅ `backend/bots/ensemble_bot.py` - Changed `super().__init__(self.name)` → `super().__init__("ensemble_bot")`
4. ✅ `backend/bots/sentiment_bot.py` - Changed `super().__init__(self.name)` → `super().__init__("sentiment_bot")`
5. ✅ `backend/bots/nifty_bot.py` - Changed `super().__init__(self.name)` → `super().__init__("nifty_bot")`
6. ✅ `backend/bots/sensex_bot.py` - Changed `super().__init__(self.name)` → `super().__init__("sensex_bot")`

## Bots Already Using String Literals (No Changes Needed)

- ✅ `backend/bots/rsi_bot.py` - Already uses `super().__init__("rsi_bot")`
- ✅ `backend/bots/macd_bot.py` - Already uses `super().__init__("macd_bot")`
- ✅ `backend/bots/ma_bot.py` - Already uses `super().__init__("ma_bot")`
- ✅ `backend/bots/ml_bot.py` - Already uses `super().__init__("ml_bot")`

## Testing

The backend should now start without the `TypeError`:

```bash
cd backend
python main.py
```

All bots should initialize correctly now! ✅

