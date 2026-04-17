import os
import shutil
import re
import datetime
import argparse
from typing import List

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_ROOT = os.path.dirname(SCRIPT_DIR) # 04_Agent_Core
PROJECTS_ROOT = os.path.dirname(SOURCE_ROOT) # Antigravity
GITHUB_ROOT = os.path.join(PROJECTS_ROOT, "GitHub")

PROJECTS = {
    "01_SolarLeadScout": "Solar_Lead_Scout",
    "02_Agent_DealTracker": "Acquisition_Tracker",
    "03_Agent_Dashboard": "Project_Portfolio_Dashboard",
    "04_Agent_Core": "Agent_Core_Framework",
    "05_Agent_InsightLabs": "Research_Discovery_Agent"
}

# EXCLUSIONS (Do not copy these)
EXCLUDE_DIRS = {".git", "__pycache__", "logs", "drafts", ".venv", "env"}
EXCLUDE_FILES = {".env", "credentials.json", "token.json", "usage.json", "projects.json"}

# REPLACEMENT MAP (Scrubbing)
SCRUB_RULES = [
    (re.compile(r"Autonomous Intelligence Systems", re.IGNORECASE), "Autonomous Intelligence Systems"),
    (re.compile(r"Autonomous Systems", re.IGNORECASE), "Autonomous Systems"),
    (re.compile(r"Intelligence Agent", re.IGNORECASE), "Intelligence Agent"),
    (re.compile(r"System Overseer", re.IGNORECASE), "System Overseer"),
    (re.compile(r"Insight Research Agent", re.IGNORECASE), "Insight Research Agent"),
    (re.compile(r"Deal Tracker", re.IGNORECASE), "Deal Tracker"),
    (re.compile(r"Agent", re.IGNORECASE), "Agent"),
    # Personal/Contextual scrubs
    (re.compile(r"bartr@Agent\.co", re.IGNORECASE), "user@example.com"),
    (re.compile(r"Agentholdings\.carrd\.co", re.IGNORECASE), "systems-hub.example.com"),
    (re.compile(r"firstenchanter\.bsky\.social", re.IGNORECASE), "agent.bsky.social"),
    (re.compile(r"c:\\Users\\bartr\\OneDrive\\Documents\\Work\\Antigravity", re.IGNORECASE), "."),
]

def scrub_content(content: str) -> str:
    """Applies all regex rules and strips non-ASCII characters."""
    for pattern, replacement in SCRUB_RULES:
        content = pattern.sub(replacement, content)
    
    # Strip non-ASCII characters (emojis, special symbols)
    # Range 0-127 covers standard English letters, numbers, and basic punctuation
    content = "".join(c for c in content if ord(c) < 128)
    
    return content

def sync_project(internal_name: str, github_name: str, force=False, dry_run=False):
    src = os.path.join(PROJECTS_ROOT, internal_name)
    dest_base = os.path.join(GITHUB_ROOT, github_name)
    
    if not os.path.exists(src):
        print(f"[ERROR] Source not found: {src}")
        return

    # Determine if this is an update or initial sync
    main_dir = os.path.join(dest_base, "main")
    updates_dir = os.path.join(dest_base, "updates")
    
    # Check if main/ exists and has files (indicating it's already been synced/uploaded)
    has_main = os.path.exists(main_dir) and any(os.scandir(main_dir))
    
    if force:
        target_dir = main_dir
        print(f"[FORCE] Syncing directly to main/ for {github_name} (Overwriting existing files).")
    elif has_main:
        # Create a branch folder for the update
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        target_dir = os.path.join(updates_dir, f"update_{timestamp}")
        print(f"[UPDATE] Update detected for {github_name}. Staging in updates/ folder.")
    else:
        # Initial sync goes directly to main
        target_dir = main_dir
        print(f"[NEW] Initial sync for {github_name}. Staging in main/ folder.")

    if dry_run:
        print(f"[DRY-RUN] Syncing {internal_name} -> {target_dir}")
        return

    print(f"Syncing {internal_name} to {github_name}...")
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    for root, dirs, files in os.walk(src):
        # Filter directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        # Calculate relative path
        rel_path = os.path.relpath(root, src)
        dest_root = os.path.join(target_dir, rel_path)
        
        if not os.path.exists(dest_root):
            os.makedirs(dest_root)
            
        for file in files:
            if file in EXCLUDE_FILES:
                continue
                
            src_file = os.path.join(root, file)
            dest_file = os.path.join(dest_root, file)
            
            # Read, Scrub, Write
            try:
                # Using utf-8-sig to handle Byte Order Marks correctly and robustly
                with open(src_file, 'r', encoding='utf-8-sig', errors='ignore') as f:
                    content = f.read()
                
                scrubbed = scrub_content(content)
                
                with open(dest_file, 'w', encoding='utf-8') as f:
                    f.write(scrubbed)
            except Exception as e:
                print(f"  [ERROR] Error processing {file}: {e}")

    print(f"  [DONE] Done. Staged in {os.path.basename(target_dir)}")

def main():
    parser = argparse.ArgumentParser(description="Synchronize internal projects to GitHub workspace.")
    parser.add_argument("--force", action="store_true", help="Overwrite the 'main' folder instead of creating an update.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be synced without making changes.")
    args = parser.parse_args()

    print("GitHub Workspace Manager")
    print("="*30)
    for internal, public in PROJECTS.items():
        sync_project(internal, public, force=args.force, dry_run=args.dry_run)
    print("\nAll projects synchronized and sanitized.")

if __name__ == "__main__":
    main()
