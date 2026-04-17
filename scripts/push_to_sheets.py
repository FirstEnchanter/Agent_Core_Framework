import json
import os
import sys
import sys
import glob
from datetime import datetime
import gspread

# Shared safe-write utility (scan  prepare  re-scan  merge  write)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sheet_utils import safe_write_worksheet

# Paths
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "token.json")
PROJECTS_JSON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard", "projects.json")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1ePSsTy_MM42tYmoKC4kZHhH_mPu1NjtRfcB0hCoGDeI/edit?gid=1979318330#gid=1979318330"

def push_projects(gc, sh):
    if not os.path.exists(PROJECTS_JSON):
        print(f"Error: {PROJECTS_JSON} not found. No projects to push.")
        return

    try:
        worksheet = sh.worksheet("Dashboard")
    except gspread.exceptions.WorksheetNotFound:
        print("Dashboard worksheet not found, creating it...")
        worksheet = sh.add_worksheet(title="Dashboard", rows="100", cols="20")

    print("Reading local projects...")
    with open(PROJECTS_JSON, 'r', encoding='utf-8') as f:
        projects = json.load(f)

    if not projects:
        print("No projects to push.")
        return

    headers = list(projects[0].keys())
    data = [[proj.get(h, "") for h in headers] for proj in projects]

    print(f"Preparing to sync {len(projects)} projects (with safe-merge)...")

    # Safe-write: scan before, merge custom rows, then write
    total = safe_write_worksheet(
        worksheet=worksheet,
        managed_headers=headers,
        managed_data=data,
        key_column=0,           # Project ID is in column A (index 0)
        sheet_label="Dashboard",
    )
    print(f"SUCCESS: {total} row(s) written to Google Sheets Dashboard tab.")

def push_agent_logs(gc, sh):
    log_dir = os.path.dirname(PROJECTS_JSON)
    root_dir = os.path.dirname(log_dir)
    history_file = os.path.join(root_dir, 'logs', 'post_history.json')
    drafts_dir = os.path.join(root_dir, 'drafts')

    logs = []
    
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for post in data.get('posts', []):
                    logs.append({
                        "Timestamp": post.get("timestamp"),
                        "Status": "Published",
                        "Platform": post.get('platform', 'bluesky').title(),
                        "Message": "Success",
                        "Source": post.get('source_id')
                    })
        except Exception as e:
            print(f"Warn: unable to read post_history.json - {e}")

    if os.path.exists(drafts_dir):
        for fp in glob.glob(os.path.join(drafts_dir, 'failed_*.md')):
            basename = os.path.basename(fp)
            parts = basename.replace('failed_', '').replace('.md', '')
            try:
                if '_' in parts:
                    dt = datetime.strptime(parts, "%Y%m%d_%H%M%S")
                else:
                    dt = datetime.strptime(parts, "%Y%m%d")
                ts = dt.isoformat()
            except:
                ts = ""
            
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    lines = f.read().strip().split('\n')
                    msg = lines[0].replace("BAE FAILURE: ", "") if lines else "Failed draft"
                logs.append({
                    "Timestamp": ts,
                    "Status": "Failed",
                    "Platform": "All",
                    "Message": msg,
                    "Source": basename
                })
            except:
                pass

    if not logs:
        print("No agent logs to push.")
        return

    logs.sort(key=lambda x: x['Timestamp'] if x['Timestamp'] else "", reverse=True)
    headers = ["Timestamp", "Status", "Platform", "Message", "Source"]
    data = [[row.get(h, "") for h in headers] for row in logs]

    try:
        worksheet = sh.worksheet("Agent Logs")
    except gspread.exceptions.WorksheetNotFound:
        print("Agent Logs worksheet not found, creating it...")
        worksheet = sh.add_worksheet(title="Agent Logs", rows="500", cols="5")

    print(f"Preparing to sync {len(logs)} agent logs...")
    
    total = safe_write_worksheet(
        worksheet=worksheet,
        managed_headers=headers,
        managed_data=data,
        key_column=0,           # Timestamp is in column A
        sheet_label="Agent Logs",
    )
    print(f"SUCCESS: {total} row(s) written to Agent Logs tab.")


def main():
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"Error: {CREDENTIALS_FILE} not found.")
        return

    print("Authenticating with Google... (Check your browser if this is the first run!)")
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

    push_projects(gc, sh)
    push_agent_logs(gc, sh)

if __name__ == "__main__":
    main()
