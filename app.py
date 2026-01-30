"""
Account Management Insights Slack Bot
Natural language queries for AM notes + operational metrics
"""

import os
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import snowflake.connector
from datetime import datetime

# Initialize Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Snowflake connection
def get_snowflake_connection():
    """Create Snowflake connection using environment variables"""
    return snowflake.connector.connect(
        account=os.environ.get("SNOWFLAKE_ACCOUNT"),
        user=os.environ.get("SNOWFLAKE_USER"),
        password=os.environ.get("SNOWFLAKE_PASSWORD"),
        authenticator=os.environ.get("SNOWFLAKE_AUTHENTICATOR", "snowflake"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "ANALYTICS"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "DBT_PRODUCTION"),
    )


def parse_am_name(text):
    """Extract Account Manager name from query"""
    # Common AM names to look for
    am_patterns = [
        r'\bmaddy\b',
        r'\bmaddie\b',
        r'\blaura\b',
        r'\btaryn\b',
        r'\bpaul\b',
        r'\bnatalie\b',
        r'\bandres\b',
        r'\bzain\b',
        r'\bemmanuel\b',
        r'\bmargareth\b',
    ]

    text_lower = text.lower()
    for pattern in am_patterns:
        if re.search(pattern, text_lower):
            return re.search(pattern, text_lower).group(0).title()
    return None


def query_am_portfolio(am_name):
    """Get AM portfolio summary"""
    conn = get_snowflake_connection()
    cursor = conn.cursor()

    query = f"""
    WITH am_user AS (
        SELECT SALESFORCE_USER_ID, FIRST_NAME, LAST_NAME, FULL_NAME, EMAIL
        FROM ANALYTICS.DBT_PRODUCTION.DIM_SALESFORCE__USERS
        WHERE FIRST_NAME ILIKE '%{am_name}%' AND IS_ACTIVE = TRUE
        LIMIT 1
    )
    SELECT
        u.FULL_NAME as account_manager,
        u.EMAIL as am_email,
        COUNT(DISTINCT sf.SALESFORCE_ACCOUNT_ID) as total_facilities,
        COUNT(CASE WHEN sf.MONTHLY_NOTES_JANUARY_2026 IS NOT NULL THEN 1 END) as jan_2026_notes,
        COUNT(CASE WHEN sf.MONTHLY_NOTES_DECEMBER_2025 IS NOT NULL THEN 1 END) as dec_2025_notes,
        LISTAGG(DISTINCT w.STATE, ', ') as states_covered
    FROM am_user u
    JOIN ANALYTICS.DBT_PRODUCTION.STG_SALESFORCE__ACCOUNTS sf
        ON u.SALESFORCE_USER_ID = sf.OWNER_ID
    LEFT JOIN ANALYTICS.DBT_PRODUCTION_CORE.DIM_WORKPLACES w
        ON sf.SALESFORCE_ACCOUNT_ID = w.SALESFORCE_ID
    GROUP BY u.FULL_NAME, u.EMAIL
    """

    cursor.execute(query)
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    return result


def query_declining_facilities(am_name=None):
    """Get facilities with declining usage"""
    conn = get_snowflake_connection()
    cursor = conn.cursor()

    am_filter = ""
    if am_name:
        am_filter = f"AND u.FIRST_NAME ILIKE '%{am_name}%'"

    query = f"""
    WITH monthly_metrics AS (
        SELECT
            w.WORKPLACE_ID,
            w.SALESFORCE_ID,
            w.NAME as facility_name,
            DATE_TRUNC('month', s.SHIFT_START_AT) as month,
            COUNT(CASE WHEN s.IS_DELETED = FALSE THEN 1 END) as total_shifts,
            SUM(CASE WHEN s.IS_DELETED = FALSE THEN s.NET_REVENUE END) as net_revenue
        FROM ANALYTICS.DBT_PRODUCTION_CORE.DIM_WORKPLACES w
        JOIN ANALYTICS.DBT_PRODUCTION_CORE.FCT_SHIFTS s
            ON w.WORKPLACE_ID = s.WORKPLACE_ID
        WHERE s.SHIFT_START_AT >= '2025-12-01'
            AND s.SHIFT_START_AT < '2026-02-01'
        GROUP BY w.WORKPLACE_ID, w.SALESFORCE_ID, w.NAME, DATE_TRUNC('month', s.SHIFT_START_AT)
    ),
    mom_comparison AS (
        SELECT
            facility_name,
            SALESFORCE_ID,
            MAX(CASE WHEN month = '2025-12-01' THEN total_shifts END) as dec_shifts,
            MAX(CASE WHEN month = '2026-01-01' THEN total_shifts END) as jan_shifts,
            MAX(CASE WHEN month = '2025-12-01' THEN net_revenue END) as dec_revenue,
            MAX(CASE WHEN month = '2026-01-01' THEN net_revenue END) as jan_revenue
        FROM monthly_metrics
        GROUP BY facility_name, SALESFORCE_ID
        HAVING dec_shifts IS NOT NULL AND jan_shifts IS NOT NULL
    )
    SELECT
        mc.facility_name,
        u.FULL_NAME as account_manager,
        mc.dec_shifts,
        mc.jan_shifts,
        mc.jan_shifts - mc.dec_shifts as shift_change,
        ROUND((mc.jan_shifts - mc.dec_shifts)::FLOAT / mc.dec_shifts * 100, 1) as pct_change,
        ROUND(mc.dec_revenue, 2) as dec_revenue,
        ROUND(mc.jan_revenue, 2) as jan_revenue
    FROM mom_comparison mc
    JOIN ANALYTICS.DBT_PRODUCTION.STG_SALESFORCE__ACCOUNTS sf
        ON mc.SALESFORCE_ID = sf.SALESFORCE_ACCOUNT_ID
    LEFT JOIN ANALYTICS.DBT_PRODUCTION.DIM_SALESFORCE__USERS u
        ON sf.OWNER_ID = u.SALESFORCE_USER_ID
    WHERE mc.jan_shifts < mc.dec_shifts
        {am_filter}
    ORDER BY pct_change ASC
    LIMIT 5
    """

    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return results


def format_portfolio_response(data):
    """Format AM portfolio summary for Slack"""
    if not data:
        return "❌ Account Manager not found"

    am_name, email, facilities, jan_notes, dec_notes, states = data

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━
👤 *{am_name}*
━━━━━━━━━━━━━━━━━━━━━━━━━
📧 {email}
🏥 *{facilities} facilities* managed
📝 {jan_notes} notes (Jan 2026)
📝 {dec_notes} notes (Dec 2025)
🗺️ States: {states if states else 'N/A'}
    """.strip()


def format_declining_facilities(results, am_name=None):
    """Format declining facilities for Slack"""
    if not results:
        return "✅ No declining facilities found!"

    header = f"📉 *Top 5 Declining Facilities*"
    if am_name:
        header += f" ({am_name}'s portfolio)"

    output = [f"━━━━━━━━━━━━━━━━━━━━━━━━━\n{header}\n━━━━━━━━━━━━━━━━━━━━━━━━━"]

    for i, row in enumerate(results, 1):
        facility, am, dec_shifts, jan_shifts, shift_change, pct_change, dec_rev, jan_rev = row

        output.append(f"""
*{i}. {facility}*
   AM: {am if am else 'N/A'}
   Shifts: {dec_shifts} → {jan_shifts} ({shift_change:+d}, {pct_change:+.1f}%)
   Revenue: ${dec_rev:,.0f} → ${jan_rev:,.0f}
        """.strip())

    return "\n\n".join(output)


@app.command("/am-insights")
def handle_am_insights_command(ack, command, say):
    """Handle /am-insights slash command"""
    ack()  # Acknowledge command immediately

    query_text = command['text'].strip()

    if not query_text:
        say("""
👋 *Welcome to AM Insights Bot!*

Ask me questions like:
• `Show me Maddy's portfolio`
• `Which facilities are declining?`
• `Show me Laura's declining facilities`
• `Give me Maddy's facilities`

Type `/am-insights <your question>`
        """.strip())
        return

    # Parse intent
    query_lower = query_text.lower()
    am_name = parse_am_name(query_text)

    try:
        # Portfolio query
        if 'portfolio' in query_lower or 'facilities' in query_lower:
            if am_name:
                say(f"🔍 Looking up {am_name}'s portfolio...")
                data = query_am_portfolio(am_name)
                response = format_portfolio_response(data)
                say(response)
            else:
                say("❌ Please specify an Account Manager name (e.g., 'Show me Maddy's portfolio')")

        # Declining facilities query
        elif 'declining' in query_lower or 'reducing' in query_lower or 'decreasing' in query_lower:
            say(f"🔍 Finding declining facilities{f' for {am_name}' if am_name else ''}...")
            results = query_declining_facilities(am_name)
            response = format_declining_facilities(results, am_name)
            say(response)

        else:
            say(f"""
🤔 I'm not sure how to help with: "{query_text}"

Try asking:
• `Show me [AM name]'s portfolio`
• `Which facilities are declining?`
• `Show me [AM name]'s declining facilities`
            """.strip())

    except Exception as e:
        say(f"❌ Error: {str(e)}\n\nPlease try again or contact support.")


@app.event("app_mention")
def handle_mention(event, say):
    """Handle @mentions of the bot"""
    text = event['text']
    # Remove the bot mention from the text
    query_text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()

    if not query_text:
        say("👋 Hi! Use `/am-insights <question>` to query AM data!")
        return

    # Process as if it were a slash command
    say(f"🔍 Analyzing: {query_text}")
    # You can reuse the logic from slash command here


@app.event("message")
def handle_dm(event, say):
    """Handle direct messages to the bot"""
    # Only respond to DMs (not channel messages)
    if event.get('channel_type') == 'im':
        text = event.get('text', '')

        if text:
            say(f"👋 Hi! Use `/am-insights {text}` to query AM data!")


if __name__ == "__main__":
    # Start the app
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    print("⚡️ AM Insights Bot is running!")
    handler.start()
