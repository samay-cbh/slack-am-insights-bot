# Railway Deployment Guide

## Quick Setup

Your bot is now on GitHub at: https://github.com/samay-cbh/slack-am-insights-bot

Follow these steps to deploy to Railway:

### 1. Create New Railway Project

1. Go to https://railway.app/
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Choose `samay-cbh/slack-am-insights-bot`
5. Railway will auto-detect the Python configuration from `runtime.txt` and `Procfile`

### 2. Configure Environment Variables

In the Railway dashboard, go to your project → Variables tab and add these:

#### Slack Credentials
```
SLACK_BOT_TOKEN=xoxb-your-actual-token
SLACK_APP_TOKEN=xapp-your-actual-app-token
SLACK_SIGNING_SECRET=your-actual-signing-secret
```

#### Snowflake Credentials
```
SNOWFLAKE_ACCOUNT=your-account.snowflakecomputing.com
SNOWFLAKE_USER=your-username
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_AUTHENTICATOR=snowflake
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=ANALYTICS
SNOWFLAKE_SCHEMA=DBT_PRODUCTION
```

**Note**: Replace all `your-actual-*` placeholders with the real values from your setup.

### 3. Deploy

1. Railway will automatically deploy after you add the environment variables
2. Watch the deployment logs in the Railway dashboard
3. Look for the success message: `⚡️ AM Insights Bot is running!`

### 4. Verify Deployment

In your Slack workspace, test the bot:

```
/am-insights Show me Maddy's portfolio
/am-insights Which facilities are declining?
/am-insights Show me Laura's declining facilities
```

### 5. Automatic Deployments

Railway is now connected to your GitHub repo. Every time you push to the `main` branch, Railway will automatically deploy the changes.

To push updates:
```bash
cd /Users/samayj/cbh-evidence/slack-am-insights-bot
git add .
git commit -m "Update bot logic"
git push origin main
```

Railway will detect the push and redeploy automatically.

## Troubleshooting

### Bot Not Responding

Check Railway logs for errors:
- Slack token issues: Verify tokens are correct and haven't expired
- Snowflake connection: Test your Snowflake credentials locally first
- Socket Mode: Ensure SLACK_APP_TOKEN is correct (starts with xapp-)

### Snowflake Connection Errors

If you see authentication errors:
1. Verify your Snowflake password is correct
2. Check that your account URL ends with `.snowflakecomputing.com`
3. Ensure your user has access to ANALYTICS database

### Deployment Fails

- Check `requirements.txt` is present and valid
- Verify `Procfile` has: `web: python app.py`
- Ensure `runtime.txt` specifies Python 3.11.7

## Monitoring

Railway provides:
- Real-time logs
- Resource usage metrics
- Deployment history
- Automatic crash recovery

Access these from your Railway project dashboard.

## Environment Variable Management

To update environment variables:
1. Go to Railway project → Variables
2. Edit the value
3. Railway will automatically redeploy with new values
4. No need to push code changes for env var updates
