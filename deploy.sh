#!/bin/bash

# 🚀 Railway Deployment Helper Script
# This script helps prepare your app for Railway deployment

set -e  # Exit on error

echo "================================================"
echo "🚀 Railway Deployment Preparation"
echo "================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check if Railway CLI is installed
echo "📦 Checking Railway CLI..."
if ! command -v railway &> /dev/null; then
    echo -e "${YELLOW}⚠️  Railway CLI not found. Installing...${NC}"
    npm install -g @railway/cli
    echo -e "${GREEN}✅ Railway CLI installed${NC}"
else
    echo -e "${GREEN}✅ Railway CLI found${NC}"
fi
echo ""

# Step 2: Check Git status
echo "📝 Checking Git status..."
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}⚠️  You have uncommitted changes${NC}"
    echo "Would you like to commit them? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        git add .
        echo "Enter commit message:"
        read -r commit_msg
        git commit -m "$commit_msg"
        echo -e "${GREEN}✅ Changes committed${NC}"
    fi
else
    echo -e "${GREEN}✅ No uncommitted changes${NC}"
fi
echo ""

# Step 3: Optimize models
echo "🔧 Optimizing ML models..."
if [ -d "backend/models" ]; then
    echo "Running model optimizer..."
    cd backend
    python ml/model_optimizer.py || echo -e "${YELLOW}⚠️  Model optimization skipped (optional)${NC}"
    cd ..
    echo -e "${GREEN}✅ Model optimization complete${NC}"
else
    echo -e "${YELLOW}⚠️  No models directory found, skipping optimization${NC}"
fi
echo ""

# Step 4: Check model sizes
echo "📊 Checking model sizes..."
if [ -d "backend/models" ]; then
    total_size=$(du -sh backend/models | cut -f1)
    echo "Total model size: $total_size"
    
    # Check if size exceeds 500MB (Railway limit)
    size_bytes=$(du -s backend/models | cut -f1)
    size_mb=$((size_bytes / 1024))
    
    if [ $size_mb -gt 500 ]; then
        echo -e "${RED}❌ Models exceed 500MB limit!${NC}"
        echo "Consider:"
        echo "  1. Running model optimizer again"
        echo "  2. Removing unused models"
        echo "  3. Setting SKIP_MODEL_LOADING=true in Railway"
    else
        echo -e "${GREEN}✅ Model size within limits${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  No models directory found${NC}"
fi
echo ""

# Step 5: Check if .env.example exists
echo "🔐 Checking environment configuration..."
if [ ! -f "env.example" ]; then
    echo -e "${RED}❌ env.example not found${NC}"
else
    echo -e "${GREEN}✅ env.example found${NC}"
    echo "Remember to set these variables in Railway dashboard:"
    echo ""
    grep -v '^#' env.example | grep -v '^$' | head -10
    echo "..."
fi
echo ""

# Step 6: Test local build
echo "🧪 Testing local build..."
echo "Would you like to test the build locally? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Installing backend dependencies..."
    cd backend
    pip install -r requirements.txt > /dev/null 2>&1 || echo -e "${YELLOW}⚠️  Some dependencies failed (may be optional)${NC}"
    cd ..
    
    echo "Installing frontend dependencies..."
    cd frontend
    npm install > /dev/null 2>&1 || echo -e "${YELLOW}⚠️  Frontend install failed${NC}"
    npm run build || echo -e "${RED}❌ Frontend build failed${NC}"
    cd ..
    
    echo -e "${GREEN}✅ Local build test complete${NC}"
fi
echo ""

# Step 7: Push to GitHub
echo "📤 Pushing to GitHub..."
echo "Would you like to push to GitHub now? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    git push origin main || git push origin master
    echo -e "${GREEN}✅ Pushed to GitHub${NC}"
fi
echo ""

# Step 8: Railway deployment
echo "🚂 Railway Deployment..."
echo "Would you like to deploy to Railway now? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Logging into Railway..."
    railway login
    
    echo ""
    echo "Is this a new project? (y/n)"
    read -r new_project
    
    if [[ "$new_project" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "Creating new Railway project..."
        railway init
        
        echo ""
        echo "Adding PostgreSQL..."
        railway add --plugin postgresql
        
        echo ""
        echo "Adding Redis..."
        railway add --plugin redis
    else
        echo "Linking to existing project..."
        railway link
    fi
    
    echo ""
    echo "Deploying to Railway..."
    railway up
    
    echo ""
    echo -e "${GREEN}✅ Deployment initiated!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Go to Railway dashboard: railway open"
    echo "2. Set environment variables (see env.example)"
    echo "3. Wait for deployment to complete"
    echo "4. Visit your app URL"
fi
echo ""

# Step 9: Summary
echo "================================================"
echo "✅ Deployment Preparation Complete!"
echo "================================================"
echo ""
echo "📚 Next Steps:"
echo "1. Set environment variables in Railway dashboard"
echo "2. Monitor deployment logs: railway logs"
echo "3. Check health endpoint: https://your-app.railway.app/health"
echo "4. Read full guide: DEPLOYMENT.md"
echo ""
echo "🆘 Need help?"
echo "- Railway Docs: https://docs.railway.app"
echo "- Project Docs: DEPLOYMENT.md"
echo ""
echo "🎉 Happy deploying!"

