"""
add_project.py â€” CLI helper to add a new project to the Agent dashboard.

Usage:
    python scripts/add_project.py "Project Name" "Short description" [--status Active]

Examples:
    python scripts/add_project.py "Lead Gen Bot" "Automates outreach via LinkedIn."
    python scripts/add_project.py "CRM Sync" "Sync contacts to HubSpot." --status Planned
"""

import json
import os
import sys
import re
from datetime import date

PROJECTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard", "projects.json")

VALID_STATUSES = {"Active", "Planned", "In Progress", "Completed", "Paused"}


def slugify(text: str) -> str:
    """Convert a name to a URL-safe ID slug."""
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def load_projects() -> list:
    if os.path.exists(PROJECTS_FILE):
        with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_projects(projects: list) -> None:
    with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(projects, f, indent=4, ensure_ascii=False)


def main():
    args = sys.argv[1:]

    # Parse positional args + optional --status flag
    name = None
    description = None
    status = "Active"

    i = 0
    positional = []
    while i < len(args):
        if args[i] == "--status" and i + 1 < len(args):
            status = args[i + 1]
            i += 2
        else:
            positional.append(args[i])
            i += 1

    if len(positional) >= 1:
        name = positional[0]
    if len(positional) >= 2:
        description = positional[1]

    if not name:
        print("ERROR: Project name is required.")
        print(__doc__)
        sys.exit(1)

    if not description:
        print("ERROR: Description is required.")
        print(__doc__)
        sys.exit(1)

    if status not in VALID_STATUSES:
        print(f"WARNING: '{status}' is not a standard status. Valid: {', '.join(sorted(VALID_STATUSES))}")
        print("Continuing with the provided status...")

    # Load, check for duplicates, append, save
    projects = load_projects()

    project_id = slugify(name)
    if any(p.get("id") == project_id for p in projects):
        print(f"ERROR: A project with ID '{project_id}' already exists.")
        print("  Rename your project or update the existing one directly in projects.json.")
        sys.exit(1)

    new_project = {
        "id":             project_id,
        "name":           name,
        "description":    description,
        "date_completed": str(date.today()),
        "status":         status,
    }

    projects.append(new_project)
    save_projects(projects)

    print(f"SUCCESS: Project '{name}' added to the dashboard.")
    print(f"  ID:     {project_id}")
    print(f"  Status: {status}")
    print(f"  Date:   {new_project['date_completed']}")
    print()
    print("Next steps:")
    print("  1. Refresh your dashboard: http://localhost:8080")
    print("  2. Sync to Google Sheets:  python scripts/push_to_sheets.py")
    print("     (or click 'Sync to Sheets' in the dashboard header)")


if __name__ == "__main__":
    main()

