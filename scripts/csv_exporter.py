import json
import csv
import os

PROJECTS_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard", "projects.json")
CSV_EXPORT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Projects_Tracker.csv")

def export_to_csv():
    if not os.path.exists(PROJECTS_JSON_PATH):
        print("No projects to export yet!")
        return

    with open(PROJECTS_JSON_PATH, 'r', encoding='utf-8') as f:
        projects = json.load(f)

    if not projects:
        print("Project database is empty.")
        return

    # Extract all keys across all projects for headers
    headers = list(projects[0].keys())

    with open(CSV_EXPORT_PATH, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for proj in projects:
            writer.writerow(proj)

    print(f"✅ Successfully exported your portfolio to {CSV_EXPORT_PATH}")
    print("You can drag and drop this generated .csv file directly into Google Sheets!")

if __name__ == "__main__":
    export_to_csv()
