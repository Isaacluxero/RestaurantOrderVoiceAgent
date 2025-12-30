# Railway Deployment Guide

This guide walks you through deploying the Voice Agent application to Railway.

## Prerequisites

- A Railway account (sign up at [railway.app](https://railway.app))
- Your repository pushed to GitHub/GitLab/Bitbucket
- All required API keys (OpenAI, Twilio)

## Deployment Steps

### 1. Connect Repository to Railway

1. Go to [railway.app](https://railway.app) and sign in
2. Click "New Project"
3. Select "Deploy from GitHub repo" (or your Git provider)
4. Choose your repository
5. Railway will automatically detect it's a Python project

### 2. Add PostgreSQL Database

1. In your Railway project, click "New"
2. Select "Database" → "PostgreSQL"
3. Railway will automatically create the database and set `DATABASE_URL` environment variable

**Important**: Use PostgreSQL on Railway, not SQLite (SQLite won't work in Railway's filesystem).

### 3. Configure Environment Variables

In Railway project settings, add these environment variables:

**Required:**
- `OPENAI_API_KEY` - Your OpenAI API key
- `TWILIO_ACCOUNT_SID` - Your Twilio Account SID
- `TWILIO_AUTH_TOKEN` - Your Twilio Auth Token
- `TWILIO_PHONE_NUMBER` - Your Twilio phone number (e.g., +19789972543)
- `RESTAURANT_NAME` - Name of your restaurant

**Note:** `DATABASE_URL` is automatically set when you add the PostgreSQL service.

### 4. Deploy

Railway will automatically:
- Detect Python and Node.js
- Install dependencies from `requirements.txt`
- Build the frontend (via `nixpacks.toml`)
- Start the server using the command in `railway.json`

### 5. Run Database Migrations

After the first deployment, run migrations:

**Option A: Via Railway CLI**
```bash
npm install -g @railway/cli
railway login
railway link  # Link to your project
railway run alembic upgrade head
```

**Option B: Via Railway Dashboard**
1. Go to your service in Railway
2. Click "Variables" tab
3. Click "New Variable"
4. Add a one-time command: `alembic upgrade head`
5. Or use the "Deployments" tab to run a one-off command

### 6. Get Your App URL

1. In Railway dashboard, go to your service
2. Click "Settings" → "Domains"
3. Railway provides a default domain (e.g., `your-app.railway.app`)
4. You can also add a custom domain

### 7. Update Twilio Webhooks

1. Go to [Twilio Console](https://console.twilio.com)
2. Navigate to Phone Numbers → Manage → Active Numbers
3. Select your phone number
4. Under "Voice & Fax", update webhook URLs:
   - **A CALL COMES IN**: `https://your-app.railway.app/webhooks/voice/incoming`
   - **CALL STATUS CHANGES**: `https://your-app.railway.app/webhooks/voice/status`
5. Set HTTP method to `POST`
6. Save

### 8. Verify Deployment

1. Visit your Railway URL to see the frontend dashboard
2. Test the health endpoint: `https://your-app.railway.app/health`
3. Make a test call to your Twilio number

## Files Created for Railway

- `railway.json` - Railway deployment configuration
- `Procfile` - Process file (alternative to railway.json)
- `requirements.txt` - Python dependencies
- `nixpacks.toml` - Build configuration for Railway
- `build.sh` - Build script (optional, nixpacks.toml is used instead)
- `.railwayignore` - Files to ignore during deployment

## Troubleshooting

### Build Fails

- Check Railway logs for errors
- Ensure `requirements.txt` has all dependencies
- Verify Node.js version compatibility (nixpacks.toml uses Node 18)

### Database Connection Errors

- Verify `DATABASE_URL` is set correctly
- Ensure PostgreSQL service is running
- Check that migrations have run: `railway run alembic upgrade head`

### Frontend Not Loading

- Check that frontend was built (look for `app/static/` directory in logs)
- Verify static files are being served correctly
- Check Railway logs for file path errors

### Port Errors

- Railway automatically sets `PORT` environment variable
- The `uvicorn` command uses `$PORT` from environment
- No configuration needed

## Monitoring

- View logs in Railway dashboard under "Deployments"
- Set up alerts for deployment failures
- Monitor resource usage in Railway dashboard

## Updating Your App

1. Push changes to your repository
2. Railway will automatically detect and redeploy
3. Run migrations if database schema changed: `railway run alembic upgrade head`

