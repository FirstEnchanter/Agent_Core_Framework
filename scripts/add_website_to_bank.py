from executor.tools.content import GoogleSheetsClient, CarrdClient
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

load_dotenv()

def main():
    print("--- Agent Content Bank Sync ---")
    
    carrd = CarrdClient()
    sheet = GoogleSheetsClient()
    
    pillars = carrd.fetch_brand_pillars()
    content_str = f"Autonomous Intelligence Systems: Building legacy through Community ({pillars['Community']}), Environment ({pillars['Environment']}), and Transparency ({pillars['Transparency']})."
    
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    row = [timestamp, "Brand", "Carrd Website", content_str, carrd.url]
    
    print(f"Attempting to add: {content_str}")
    
    try:
        sheet.append_row(row)
        print("\nSUCCESS: Website content synced to Google Sheets bank.")
    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nNote: The first time you run this, a browser window will open to authorize your Google account.")

if __name__ == "__main__":
    main()
