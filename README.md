# AM Insights Slack Bot

Natural language Slack bot for querying Account Manager notes and operational metrics.

## Features

- `/am-insights` slash command for natural language queries
- Query AM portfolios, declining facilities, revenue trends
- Real-time Snowflake data integration
- Socket Mode (no webhooks needed!)

## Quick Start

### Local Testing

1. Copy `.env.example` to `.env` and fill in your credentials
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python app.py`

### Deploy to Railway

1. Push to GitHub
2. Connect Railway to your repo
3. Add environment variables in Railway dashboard
4. Deploy!

## Usage Examples

```
/am-insights Show me Maddy's portfolio
/am-insights Which facilities are declining?
/am-insights Show me Laura's declining facilities
```

## Environment Variables

Required:
- `SLACK_BOT_TOKEN` - Bot OAuth token (starts with xoxb-)
- `SLACK_APP_TOKEN` - App-level token (starts with xapp-)
- `SLACK_SIGNING_SECRET` - From Slack app settings
- `SNOWFLAKE_ACCOUNT` - Snowflake account URL
- `SNOWFLAKE_USER` - Snowflake username
- `SNOWFLAKE_PASSWORD` - Snowflake password

Optional:
- `SNOWFLAKE_WAREHOUSE` - Default: COMPUTE_WH
- `SNOWFLAKE_DATABASE` - Default: ANALYTICS
- `SNOWFLAKE_SCHEMA` - Default: DBT_PRODUCTION
