import os
import sys
import gspread

# Shared safe-write utility (scan  prepare  re-scan  merge  write)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sheet_utils import safe_write_worksheet

CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "token.json")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ePSsTy_MM42tYmoKC4kZHhH_mPu1NjtRfcB0hCoGDeI/edit?gid=1979318330#gid=1979318330"

# 
#  FULL SETTINGS & EXECUTION REGISTRY
#  Columns: Category | Key / Command | Value / Script File | Description
# 

HEADERS = ["Category", "Key / Command", "Value / Script File", "Description"]

DATA = [
    #  SECTION: Antigravity Dashboard 
    [" ANTIGRAVITY DASHBOARD ", "", "", ""],
    ["Dashboard", "Start Command",         "Start_Dashboard.bat",                               "Double-click to launch the Autonomous Intelligence Systems Project Dashboard"],
    ["Dashboard", "Server Script",         "scripts/dashboard_server.py",                     "HTTP server serving the dashboard on localhost:8080"],
    ["Dashboard", "Dashboard UI",          "dashboard/index.html",                            "Main dashboard front-end (HTML + embedded JS)"],
    ["Dashboard", "Dashboard Styles",      "dashboard/styles.css",                            "Stylesheet for the Antigravity dashboard"],
    ["Dashboard", "Projects Data",         "dashboard/projects.json",                         "Live project data consumed by the dashboard"],
    ["Dashboard", "Usage Data",            "dashboard/usage.json",                            "Local AI token usage & cost data consumed by the dashboard"],
    ["Dashboard", "Dashboard Port",        "8080",                                            "Localhost port the dashboard server listens on"],
    ["Dashboard", "API: Sessions",         "GET /api/usage",                                  "Returns session count from Antigravity conversation store"],
    ["Dashboard", "API: Billing",          "GET /api/billing_usage",                          "Returns OpenAI/Gemini cost and token totals from usage.json"],
    ["Dashboard", "API: Projects",         "GET /api/projects",                               "Returns live project data from projects.json"],

    #  SECTION: Business Tracker Dashboard 
    [" BUSINESS TRACKER ", "", "", ""],
    ["Business Tracker", "Dashboard UI",   "BusinessTracker/index.html",                      "Business acquisition lead tracker front-end (HTML)"],
    ["Business Tracker", "App Logic",      "BusinessTracker/app.js",                          "All execution logic for the Business Tracker (23KB)"],
    ["Business Tracker", "Styles",         "BusinessTracker/style.css",                       "Stylesheet for the Business Tracker dashboard"],

    #  SECTION: Agent Agent  Main Entrypoint 
    [" Agent AGENT (MAIN) ", "", "", ""],
    ["Agent", "Run Agent",                 "python main.py run <directive>",                  "Execute a directive through the full 3-layer pipeline"],
    ["Agent", "Validate Directive",        "python main.py validate <directive>",             "Validate a directive against the required 7-section template"],
    ["Agent", "List Directives",           "python main.py list-directives",                  "List all available directives in the /directives folder"],
    ["Agent", "Bluesky Auto-Post",         "run_agent.bat",                                   "Runs the bluesky-auto-post directive; logs to logs/scheduler.log"],
    ["Agent", "Directives Dir",            "directives/",                                     "Folder containing all .md directive files for the agent"],
    ["Agent", "Logs Dir",                  "logs/",                                           "Output directory for agent run logs"],

    #  SECTION: Discord Command Center Bot 
    [" DISCORD COMMAND CENTER ", "", "", ""],
    ["Discord Bot", "Start Bot",           "python scripts/command_center.py",                "Launch the Agent Discord bot (Staff Officer)"],
    ["Discord Bot", "Bot Token Env Var",   "DISCORD_BOT_TOKEN",                               "Discord bot token loaded from .env"],
    ["Discord Bot", "Guild ID Env Var",    "DISCORD_GUILD_ID",                                "Target Discord server ID loaded from .env"],
    ["Discord Bot", "Config File",         "data/config.json",                                "Runtime config (goal, vips, urgency, tone, threshold, filing)"],
    ["Discord Bot", "Triage Interval",     "15 minutes",                                      "Automatic background email triage sweep frequency"],
    ["Discord Bot", "Slash: /settings",    "/settings",                                       "Open the Agent Control Panel (sensitivity, tone, filing, VIPs)"],
    ["Discord Bot", "Slash: /goal",        "/goal <new_goal>",                                "Update the AI triage business goal at runtime"],
    ["Discord Bot", "Slash: /urgency",     "/urgency <triggers>",                             "Update comma-separated urgency trigger keywords"],
    ["Discord Bot", "Slash: /sweep",       "/sweep [rescan_latest]",                          "Force an immediate inbox + spam triage sweep"],
    ["Discord Bot", "Slash: /help",        "/help",                                           "Display the Agent Operational Manual in Discord"],

    #  SECTION: Background Agent Daemon 
    [" BACKGROUND AGENT DAEMON ", "", "", ""],
    ["Autopilot", "Start Daemon",          "python scripts/background_agent.py",              "Launch the 24/7 autonomous email triage daemon (Layer 2)"],
    ["Autopilot", "Config File",           "data/config.json",                                "Shared runtime config used by autopilot and command center"],
    ["Autopilot", "Sleep Interval",        "15 minutes",                                      "Time between autopilot triage cycles"],

    #  SECTION: Triage Server (FastAPI) 
    [" TRIAGE SERVER (FastAPI) ", "", "", ""],
    ["Triage Server", "Start Server",      "python scripts/triage_server.py",                 "Launch the FastAPI triage server on port 8000"],
    ["Triage Server", "Server Port",       "8000",                                            "Port the FastAPI triage server listens on"],
    ["Triage Server", "Web UI Dir",        "web/",                                            "Static files directory served by the triage server"],
    ["Triage Server", "API: Test Conn",    "POST /api/test_connection",                       "Test IMAP email connection with provided credentials"],
    ["Triage Server", "API: Triage",       "POST /api/triage",                                "Run a full email triage cycle; saves config to data/config.json"],

    #  SECTION: Google Sheets Sync 
    [" GOOGLE SHEETS SYNC ", "", "", ""],
    ["Sheets Sync", "Push Projects",       "python scripts/push_to_sheets.py",                "Sync projects.json  Google Sheets 'Dashboard' tab"],
    ["Sheets Sync", "Rebuild Settings",    "python scripts/rebuild_settings_sheet.py",          "Rebuild the Settings tab in Google Sheets (safe-merge, never erases custom rows)"],
    ["Sheets Sync", "Export Research",     "python scripts/export_automation_research.py",      "Push automation research data to the 'Automation Research' tab"],
    ["Sheets Sync", "Export CSV",          "python scripts/csv_exporter.py",                    "Export projects.json to Projects_Tracker.csv for manual import"],
    ["Sheets Sync", "Add Project CLI",     "python scripts/add_project.py \"Name\" \"Desc\"",     "CLI helper to add a new project to the dashboard and projects.json"],
    ["Sheets Sync", "Spreadsheet ID",      "1ePSsTy_MM42tYmoKC4kZHhH_mPu1NjtRfcB0hCoGDeI", "Google Sheets spreadsheet ID (shared across all sync scripts)"],
    ["Sheets Sync", "Auth Credentials",    "credentials.json",                                "OAuth client credentials file for Google Sheets access"],
    ["Sheets Sync", "Auth Token",          "token.json",                                      "Cached OAuth user token (auto-refreshed)"],

    #  SECTION: Token Logger 
    [" TOKEN / USAGE LOGGER ", "", "", ""],
    ["Token Logger", "Script",             "scripts/token_logger.py",                         "Utility module  log OpenAI and Gemini token usage locally"],
    ["Token Logger", "Usage Output File",  "dashboard/usage.json",                            "JSON file storing cumulative token counts and cost estimates"],
    ["Token Logger", "OpenAI Cost Model",  "gpt-4o: $0.005/1K prompt, $0.015/1K completion", "Cost estimate rates used by log_openai_usage()"],
    ["Token Logger", "Gemini Cost Model",  "gemini-1.5-pro: $1.25/1M prompt, $3.75/1M comp", "Cost estimate rates used by log_gemini_usage()"],

    #  SECTION: Brand & Content Settings 
    [" BRAND & CONTENT SETTINGS ", "", "", ""],
    ["Brand", "SUBSTACK_PUBLICATION_URL",  "https://1stenchanter.substack.com/",              "Substack blog URL  primary content source for Bluesky posts"],
    ["Brand", "LINKTREE_URL",              "https://linktr.ee/1stenchanter",                  "Mandatory CTA link appended to all Bluesky posts"],
    ["Brand", "POSTING_SCHEDULE",          "Mon,Wed,Fri",                                     "Days of the week the Bluesky agent publishes"],
    ["Brand", "POSTING_ROTATION",          "Substack,Service,Podcast,Service,Evergreen",      "Content type rotation strategy for post variety"],
    ["Brand", "BRAND_PILLAR_COMMUNITY",    "Building legacy through Fellowship and shared goals.", "Core brand pillar  Community"],
    ["Brand", "BRAND_PILLAR_ENVIRONMENT",  "Sustainable practices and intentional growth.",   "Core brand pillar  Environment"],
    ["Brand", "BRAND_PILLAR_TRANSPARENCY", "Openness to public scrutiny and process clarity.","Core brand pillar  Transparency"],

    #  SECTION: External Service Settings 
    [" EXTERNAL SERVICE SETTINGS ", "", "", ""],
    ["Bluesky", "BLUESKY_HANDLE",          "agent.bsky.social",                      "Bluesky account handle used for publishing"],
    ["Bluesky", "BLUESKY_EMAIL",           "1stenchanter.tv@gmail.com",                       "Bluesky account email"],
    ["Email",   "SMTP_HOST",               "smtp.gmail.com",                                  "SMTP server for outgoing email escalations"],
    ["Email",   "SMTP_PORT",               "587",                                             "SMTP port (TLS)"],
    ["Email",   "SMTP_USER",               "1stenchanter.tv@gmail.com",                       "SMTP sender email address"],
    ["Email",   "ESCALATION_EMAIL",        "1stenchanter.tv@gmail.com",                       "Recipient address for critical agent failure alerts"],
    ["System",  "AGENT_ID",                "Agent-bluesky-agent",                          "Unique identifier for the Bluesky automation agent"],
    ["System",  "OPENAI_DEFAULT_MODEL",    "gpt-4o",                                          "Default OpenAI model used across all agent tools"],
    ["System",  "OPENAI_TEMPERATURE",      "0.3",                                             "OpenAI sampling temperature (lower = more deterministic)"],
    ["System",  "LOG_LEVEL",               "INFO",                                            "Logging verbosity level for all agent modules"],
    ["System",  "LOG_DIR",                 "logs/",                                           "Directory where agent log files are written"],
    ["System",  "DRAFTS_DIR",              "drafts/",                                         "Directory where content drafts are staged before publishing"],
]


def rebuild_settings():
    print("Authenticating with Google...")
    gc = gspread.oauth(
        credentials_filename=CREDENTIALS_FILE,
        authorized_user_filename=TOKEN_FILE
    )

    print("Opening spreadsheet...")
    try:
        sh = gc.open_by_url(SHEET_URL)
    except Exception as e:
        print(f"Failed to open Google Sheet. Ensure your account has access. Error: {e}")
        return

    # Find or create the Settings sheet
    try:
        worksheet = sh.worksheet("Settings")
        print("Found 'Settings' worksheet.")
    except gspread.exceptions.WorksheetNotFound:
        print("'Settings' worksheet not found, creating it...")
        worksheet = sh.add_worksheet(title="Settings", rows="120", cols="4")

    # Delegate to shared safe-write utility (scan -> prepare -> re-scan -> merge -> write)
    total = safe_write_worksheet(
        worksheet=worksheet,
        managed_headers=HEADERS,
        managed_data=DATA,
        key_column=1,
        sheet_label="Settings",
    )
    print(f"SUCCESS: Settings sheet rebuilt. {total} data row(s) written.")


if __name__ == "__main__":
    rebuild_settings()
