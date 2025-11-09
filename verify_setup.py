#!/usr/bin/env python3
"""
Setup verification script for Trading Prediction App
Checks if all dependencies and configurations are correct
"""
import sys
import subprocess
import os

def check_python_version():
    """Check if Python version is 3.8+"""
    print("Checking Python version...", end=" ")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor} (Need 3.8+)")
        return False

def check_package(package_name):
    """Check if a Python package is installed"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def check_backend_dependencies():
    """Check if backend dependencies are installed"""
    print("\nChecking backend dependencies...")
    
    packages = {
        "fastapi": "FastAPI",
        "uvicorn": "Uvicorn",
        "sqlalchemy": "SQLAlchemy",
        "yfinance": "yfinance",
        "pandas": "pandas",
        "pandas_ta": "pandas-ta",
        "sklearn": "scikit-learn",
        "apscheduler": "APScheduler",
    }
    
    all_installed = True
    for package, name in packages.items():
        if check_package(package):
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name} (Not installed)")
            all_installed = False
    
    return all_installed

def check_backend_files():
    """Check if backend files exist"""
    print("\nChecking backend files...")
    
    files = [
        "backend/main.py",
        "backend/database.py",
        "backend/freddy_merger.py",
        "backend/config.py",
        "backend/requirements.txt",
        "backend/bots/rsi_bot.py",
        "backend/bots/macd_bot.py",
        "backend/bots/ma_bot.py",
        "backend/bots/ml_bot.py",
        "backend/routes/history.py",
        "backend/routes/prediction.py",
        "backend/routes/evaluation.py",
        "backend/utils/data_fetcher.py",
        "backend/utils/indicators.py",
    ]
    
    all_exist = True
    for file in files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} (Missing)")
            all_exist = False
    
    return all_exist

def check_frontend_files():
    """Check if frontend files exist"""
    print("\nChecking frontend files...")
    
    files = [
        "frontend/package.json",
        "frontend/vite.config.js",
        "frontend/index.html",
        "frontend/src/main.js",
        "frontend/src/App.vue",
        "frontend/src/components/ChartComponent.vue",
        "frontend/src/services/api.js",
        "frontend/src/services/socket.js",
    ]
    
    all_exist = True
    for file in files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} (Missing)")
            all_exist = False
    
    return all_exist

def check_node():
    """Check if Node.js is installed"""
    print("\nChecking Node.js...")
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"  ✅ Node.js {version}")
            return True
        else:
            print("  ❌ Node.js (Not found)")
            return False
    except FileNotFoundError:
        print("  ❌ Node.js (Not installed)")
        return False

def check_npm():
    """Check if npm is installed"""
    print("Checking npm...")
    try:
        result = subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"  ✅ npm {version}")
            return True
        else:
            print("  ❌ npm (Not found)")
            return False
    except FileNotFoundError:
        print("  ❌ npm (Not installed)")
        return False

def check_env_file():
    """Check if .env file exists"""
    print("\nChecking configuration...")
    if os.path.exists("backend/.env"):
        print("  ✅ backend/.env exists")
        return True
    else:
        print("  ⚠️  backend/.env not found (Will use defaults)")
        print("     You can copy backend/.env.example to backend/.env")
        return True  # Not critical

def main():
    """Run all checks"""
    print("=" * 60)
    print("🔍 Trading Prediction App - Setup Verification")
    print("=" * 60)
    
    checks = {
        "Python Version": check_python_version(),
        "Backend Dependencies": check_backend_dependencies(),
        "Backend Files": check_backend_files(),
        "Frontend Files": check_frontend_files(),
        "Node.js": check_node(),
        "npm": check_npm(),
        "Configuration": check_env_file(),
    }
    
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:.<40} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All checks passed! You're ready to run the app!")
        print("\nNext steps:")
        print("1. cd backend && python main.py")
        print("2. Open new terminal: cd frontend && npm run dev")
        print("3. Open browser: http://localhost:3000")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\nQuick fixes:")
        print("- Install Python packages: cd backend && pip install -r requirements.txt")
        print("- Install Node packages: cd frontend && npm install")
        print("- Check README.md for detailed instructions")
        return 1

if __name__ == "__main__":
    sys.exit(main())

