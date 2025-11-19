# External Storage Setup Guide

This guide explains how to configure the ML Trading Bot to use an external hard disk for storing large ML datasets and trained models, while keeping minimal data on your main machine.

## Overview

The system supports storing data in three locations:
1. **Models** - Trained ML model files (.keras, .pkl, .h5, etc.)
2. **Data Pipeline** - Raw, bronze, and silver layer Parquet files
3. **Database** - SQLite database (can be moved but typically kept local for performance)

## Benefits of External Storage

- **Save disk space** on your main machine
- **Store large datasets** without filling up your primary drive
- **Portable data** - Easy to backup or move between machines
- **Keep minimal local data** - Only recent data cached locally

## Configuration

### Step 1: Mount Your External Drive

#### macOS
```bash
# External drive is typically mounted at /Volumes/YourDriveName
# Check available volumes
ls /Volumes/

# Example: If your drive is named "MLData"
# Path would be: /Volumes/MLData/ml-trading-data
```

#### Linux
```bash
# Mount external drive (if not auto-mounted)
sudo mkdir -p /mnt/external
sudo mount /dev/sdb1 /mnt/external

# Create directory structure
mkdir -p /mnt/external/ml-trading-data/{models,data}
```

#### Windows
```
# External drive is typically D:, E:, etc.
# Create directory structure
mkdir D:\ml-trading-data\models
mkdir D:\ml-trading-data\data
```

### Step 2: Create Directory Structure

Create the following directories on your external drive:

```bash
# On macOS/Linux
mkdir -p /Volumes/YourDrive/ml-trading-data/models
mkdir -p /Volumes/YourDrive/ml-trading-data/data/{raw,bronze,silver,experiments}

# On Windows
mkdir D:\ml-trading-data\models
mkdir D:\ml-trading-data\data\raw
mkdir D:\ml-trading-data\data\bronze
mkdir D:\ml-trading-data\data\silver
mkdir D:\ml-trading-data\data\experiments
```

### Step 3: Update .env File

Edit your `.env` file in the project root:

```env
# External Storage Configuration
# Use absolute paths for external storage

# macOS Example
DATA_ROOT=/Volumes/MyDrive/ml-trading-data/data
MODEL_STORAGE_PATH=/Volumes/MyDrive/ml-trading-data/models

# Linux Example
# DATA_ROOT=/mnt/external/ml-trading-data/data
# MODEL_STORAGE_PATH=/mnt/external/ml-trading-data/models

# Windows Example
# DATA_ROOT=D:\ml-trading-data\data
# MODEL_STORAGE_PATH=D:\ml-trading-data\models

# For local storage (default)
# DATA_ROOT=data
# MODEL_STORAGE_PATH=models
```

### Step 4: Set Permissions (Linux/macOS)

Ensure the application has write permissions:

```bash
# macOS/Linux
chmod -R 755 /Volumes/YourDrive/ml-trading-data
# Or if using a specific user
chown -R $USER:$USER /Volumes/YourDrive/ml-trading-data
```

### Step 5: Verify Configuration

Restart your backend server and check the logs:

```bash
# The system will automatically create directories if they don't exist
# Check logs for any permission errors
tail -f logs/backend-*.log
```

## What Gets Stored Where

### External Drive (Heavy Data)
- **Trained Models**: All `.keras`, `.pkl`, `.h5` model files
- **Parquet Datasets**: Raw, bronze, silver layer data files
- **Training Experiments**: Experiment logs and artifacts
- **Historical Data**: Large historical datasets

### Local Machine (Minimal Data)
- **SQLite Database**: Recent candles, predictions, training records (typically < 100MB)
- **Redis Cache**: Hot cache for recent data (in-memory or small local Redis)
- **Application Code**: Source code and dependencies
- **Logs**: Application logs

## Migration Guide

### Moving Existing Data to External Drive

1. **Stop the application**:
   ```bash
   ./stop.sh
   ```

2. **Copy existing data**:
   ```bash
   # Copy models
   cp -r backend/models/* /Volumes/YourDrive/ml-trading-data/models/
   
   # Copy data pipeline files
   cp -r backend/data/* /Volumes/YourDrive/ml-trading-data/data/
   ```

3. **Update .env** with new paths

4. **Restart the application**:
   ```bash
   ./start.sh
   ```

### Moving Database (Optional)

The database can also be moved, but it's recommended to keep it local for performance:

```env
# Move database to external drive (not recommended for production)
DATABASE_URL=sqlite:////Volumes/YourDrive/ml-trading-data/trading_predictions.db
```

**Note**: SQLite on external drives may have slower performance. Consider keeping the database local and only moving large datasets/models.

## Performance Considerations

### Best Practices

1. **Keep Database Local**: SQLite performs best on local SSD
2. **Use Fast External Drive**: USB 3.0+ or Thunderbolt for better I/O
3. **SSD Preferred**: External SSD performs better than HDD for model loading
4. **Cache Strategy**: Keep frequently accessed models/data in local cache

### Model Loading Performance

- Models are loaded on-demand when predictions are requested
- First load may be slower from external drive
- Subsequent loads benefit from OS-level caching
- Consider keeping frequently used models on local SSD

## Troubleshooting

### Permission Denied Errors

```bash
# Check permissions
ls -la /Volumes/YourDrive/ml-trading-data

# Fix permissions
chmod -R 755 /Volumes/YourDrive/ml-trading-data
```

### Drive Not Mounted

```bash
# macOS: Check if drive is mounted
ls /Volumes/

# Linux: Check mount points
df -h | grep external

# Windows: Check drive letters
dir D:\
```

### Path Not Found

- Ensure absolute paths start with `/` (macOS/Linux) or drive letter (Windows)
- Use forward slashes `/` even on Windows in .env file
- Check that directories exist or are auto-created

### Slow Performance

- Use USB 3.0+ or Thunderbolt connection
- Consider external SSD instead of HDD
- Keep frequently accessed data local
- Use Redis cache for hot data

## Example Configuration

### Complete .env Example

```env
# External Storage (macOS)
DATA_ROOT=/Volumes/MLData/ml-trading-data/data
MODEL_STORAGE_PATH=/Volumes/MLData/ml-trading-data/models

# Database (keep local for performance)
DATABASE_URL=sqlite:///./trading_predictions.db

# Other settings...
DEFAULT_SYMBOL=TCS.NS
PREDICTION_INTERVAL=300
```

## Backup Recommendations

Since your data is on an external drive, consider:

1. **Regular Backups**: Backup the external drive to cloud storage
2. **Version Control**: Use the built-in versioning system for datasets
3. **Model Snapshots**: Keep multiple versions of trained models
4. **Database Backup**: Regularly backup the SQLite database

## Summary

✅ **External storage is fully supported**  
✅ **Configure via .env file**  
✅ **Automatic directory creation**  
✅ **Works on macOS, Linux, and Windows**  
✅ **Keep database local for best performance**  

The system will automatically use the configured paths for all model and data storage operations.

