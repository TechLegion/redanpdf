# Docker Deployment Guide for Email-Based Validation

## Overview
This guide explains how to deploy the email-based file validation system using Docker on Render.

## What We've Set Up

### 1. **Docker Configuration** ✅
- **Updated Dockerfile**: Added migration step to startup script
- **Startup script**: `pdf_saas_app/start.sh` handles migrations and app startup
- **Render config**: Updated `render.yaml` to use Docker

### 2. **Migration Process** ✅
- **Alembic migration**: `20250127_add_owner_email_to_documents.py`
- **Automatic execution**: Runs every time the container starts
- **Error handling**: Graceful fallback if migrations fail

## How It Works

### **Docker Build Process:**
1. **Base image**: Python 3.11 with system dependencies
2. **Dependencies**: Installs Python packages from requirements.txt
3. **App copy**: Copies all application files
4. **Permissions**: Sets proper file permissions
5. **Startup script**: Makes migration script executable

### **Container Startup Process:**
1. **Migration**: Runs `alembic upgrade head`
2. **App start**: Starts FastAPI with Uvicorn
3. **Health check**: Monitors application health

## File Structure

```
project/
├── Dockerfile                    # Docker configuration
├── render.yaml                   # Render deployment config
├── requirements.txt              # Python dependencies
└── pdf_saas_app/
    ├── start.sh                  # Startup script (NEW)
    ├── alembic/                  # Database migrations
    │   └── versions/
    │       └── 20250127_add_owner_email_to_documents.py
    └── app/                      # FastAPI application
        ├── api/
        ├── db/
        └── services/
```

## Deployment Process

### **1. Build Phase (Docker):**
```dockerfile
# Install system dependencies
RUN apt-get update && apt-get install -y ...

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy application files
COPY . .

# Make startup script executable
RUN chmod +x /app/pdf_saas_app/start.sh
```

### **2. Runtime Phase (Container Start):**
```bash
# Run database migrations
alembic upgrade head

# Start FastAPI application
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## What Happens During Deployment

### **Step 1: Docker Build**
- Render builds the Docker image
- Installs all dependencies
- Copies application code
- Sets up permissions

### **Step 2: Container Start**
- Container starts and runs `start.sh`
- Script runs database migrations
- Script starts FastAPI application
- Health checks begin

### **Step 3: Migration Execution**
```sql
-- Adds owner_email column
ALTER TABLE documents ADD COLUMN owner_email VARCHAR(255);

-- Creates index
CREATE INDEX idx_documents_owner_email ON documents(owner_email);

-- Populates existing data
UPDATE documents 
SET owner_email = u.email 
FROM users u 
WHERE documents.owner_id = u.id;
```

## Expected Logs

### **Successful Deployment:**
```
🚀 Starting PDF SaaS Application...
📊 Running database migrations...
INFO  [alembic.runtime.migration] Context impl PostgreSQLImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade -> add_owner_email_001
✅ Database migrations completed successfully!
🌐 Starting FastAPI application...
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### **If Migration Fails:**
```
🚀 Starting PDF SaaS Application...
📊 Running database migrations...
ERROR: Migration failed: connection refused
⚠️  Continuing with startup...
🌐 Starting FastAPI application...
```

## Benefits of Docker Approach

### **1. Consistency**
- Same environment in development and production
- No dependency conflicts
- Reproducible builds

### **2. Reliability**
- Migrations run automatically on every deployment
- No manual intervention required
- Graceful error handling

### **3. Scalability**
- Easy to scale horizontally
- Container orchestration ready
- Resource isolation

## Troubleshooting

### **Common Issues:**

#### **1. Migration Fails**
- **Check**: Database connection in environment variables
- **Solution**: Verify `DATABASE_URL` is correct
- **Fallback**: App still starts, just without new features

#### **2. Container Won't Start**
- **Check**: Docker build logs
- **Solution**: Verify all dependencies are installed
- **Debug**: Check startup script permissions

#### **3. Health Check Fails**
- **Check**: Application logs
- **Solution**: Verify FastAPI is running on correct port
- **Debug**: Check health endpoint exists

## Monitoring

After deployment, monitor:
- **Container logs** in Render dashboard
- **Health check status** (should be green)
- **Database migration success** (check logs)
- **Application performance** (response times)

## Rollback Plan

If issues occur:
1. **Revert code** to previous commit
2. **Push to trigger** new Docker build
3. **Render deploys** the previous version
4. **Database remains** in current state (migrations are additive)

## Next Steps

1. **Commit and push** all changes
2. **Monitor deployment** in Render dashboard
3. **Verify migration** success in logs
4. **Test application** functionality
5. **Confirm file access** works with email validation

The Docker approach is much cleaner and more reliable than the previous method! 🐳🎉
