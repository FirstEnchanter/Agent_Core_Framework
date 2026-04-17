"""
export_automation_research.py

Exports automation research data to the 'Automation Research' tab in Google Sheets.
Uses the shared safe-write pattern: scan  prepare  re-scan  merge  write.
"""

import os
import sys
import gspread
from dotenv import load_dotenv

load_dotenv()

# Shared safe-write utility
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sheet_utils import safe_write_worksheet

CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "token.json")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ePSsTy_MM42tYmoKC4kZHhH_mPu1NjtRfcB0hCoGDeI/edit?gid=1979318330#gid=1979318330"

TAB_NAME = "Automation Research"

HEADERS = ["Category", "Agent / Platform", "Use Case", "Status", "Why (Rationale)"]

DATA = [
    ["Communication",     "Microsoft Copilot",  "Email triage, drafting, scheduling",            "Most Requested", "Solves immediate, personal time-sink for every employee."],
    ["Communication",     "Lindy AI",            "Personal assistant, scheduling, email",         "Most Requested", "High familiarity and ease of adoption."],
    ["Integration",       "Zapier / Make",       "Connecting apps, basic data moves",             "Most Requested", "Massive app ecosystem; the default 'no-code' gateway."],
    ["Support",           "Custom FAQ Bots",     "24/7 basic customer inquiry handling",          "Most Requested", "Highly visible improvement in service speed."],
    ["Orchestration",     "GenFuse AI / n8n",    "End-to-end multi-step business logic",          "Most Useful",    "Reduces automation sprawl; handles complex 'if/then' scenarios."],
    ["Orchestration",     "Relay.app",           "Workflow trigger/action automation",            "Most Useful",    "Modern, cleaner UX for complex Human-in-the-loop workflows."],
    ["Knowledge",         "Glean / Sana",        "Internal company data search & chat",           "Most Useful",    "Turns unorganized docs into an actionable, searchable asset."],
    ["Project Execution", "CrewAI / AutoGPT",    "Multi-agent collaboration (Researcher+Writer)", "Most Useful",    "Mimics human team roles for complex content/strategy projects."],
    ["Strategic Growth",  "Relevance AI",        "Data analysis and reporting agents",            "Most Useful",    "Drives decision-making based on historical firm data."],
]


def main():
    print(f"--- Exporting Automation Research to Google Sheets ({TAB_NAME}) ---")

    print("Authenticating with Google...")
    gc = gspread.oauth(
        credentials_filename=CREDENTIALS_FILE,
        authorized_user_filename=TOKEN_FILE
    )

    print("Opening spreadsheet...")
    try:
        sh = gc.open_by_url(SHEET_URL)
    except Exception as e:
        print(f"ERROR: Failed to open spreadsheet: {e}")
        return

    # Find or create the tab
    try:
        worksheet = sh.worksheet(TAB_NAME)
        print(f"Found '{TAB_NAME}' worksheet.")
    except gspread.exceptions.WorksheetNotFound:
        print(f"'{TAB_NAME}' not found  creating it...")
        worksheet = sh.add_worksheet(title=TAB_NAME, rows="50", cols="5")

    # Safe-write: scan  prepare  re-scan  merge  write
    total = safe_write_worksheet(
        worksheet=worksheet,
        managed_headers=HEADERS,
        managed_data=DATA,
        key_column=1,           # "Agent / Platform" is the unique key (column B)
        sheet_label=TAB_NAME,
    )
    print(f"SUCCESS: {total} row(s) written to '{TAB_NAME}' tab.")
    print(f"Spreadsheet ID: {os.environ.get('GOOGLE_SHEETS_SPREADSHEET_ID')}")


if __name__ == "__main__":
    main()
