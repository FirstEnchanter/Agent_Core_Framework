"""
Content / Source Tools  Layer 3: Execution

Tool Class 1: Content / Source Tools (from CLAUDE.md)

Approved sources:
    - Google Sheets
    - Substack
    - OneDrive
    - Bluesky (read/fetch)
    - Autonomous Systems Website (Carrd)

Source Integrity Rule (strict mode):
    - Agents must NOT replace approved sources
    - Use approved sources as primary material
    - Supplement only with strictly verifiable context
    - Never introduce claims that alter meaning
"""

import os
import httpx
from typing import Any, Optional
from executor.tools.logging_tool import get_logger

log = get_logger(__name__)


# 
# Google Sheets
# 

class GoogleSheetsClient:
    """
    Manages Google Sheets integration via Official API.
    Supports both reading (fetch_all_data) and writing (append_row).
    """
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    def __init__(self, spreadsheet_id: Optional[str] = None):
        self.spreadsheet_id = spreadsheet_id or os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID")
        self._service = None

    def _get_service(self):
        """Authenticated Sheets API service."""
        if self._service:
            return self._service

        import os.path
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None
        # The file token.json stores the user's access and refresh tokens
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    log.error("sheets.credentials_missing", path="credentials.json")
                    raise FileNotFoundError("credentials.json not found in project root.")
                
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        self._service = build('sheets', 'v4', credentials=creds)
        return self._service

    def fetch_all_data(self, range_name: str = "Approved Sources!A:Z") -> str:
        """Fetch sheet data as a block of text for LLM grounding."""
        if not self.spreadsheet_id:
            return ""
        
        log.info("sheets.fetch_started", spreadsheet_id=self.spreadsheet_id)
        try:
            service = self._get_service()
            result = service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range=range_name).execute()
            rows = result.get('values', [])
            
            if not rows:
                return ""

            # Convert to CSV-like text block
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerows(rows)
            return output.getvalue()

        except Exception as e:
            log.error("sheets.fetch_failed", error=str(e))
            return ""

    def append_row(self, values: list[Any], range_name: str = "Approved Sources!A:A") -> None:
        """
        Append a row to the content bank.
        """
        if not self.spreadsheet_id:
            log.warning("sheets.no_id_to_append")
            return

        log.info("sheets.append_row", items=len(values))
        try:
            service = self._get_service()
            body = {'values': [values]}
            service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body
            ).execute()
        except Exception as e:
            log.error("sheets.append_failed", error=str(e))
            raise

    def create_sheet(self, title: str) -> None:
        """Create a new tab in the spreadsheet."""
        if not self.spreadsheet_id:
            return
        log.info("sheets.create_sheet", title=title)
        try:
            service = self._get_service()
            body = {'requests': [{'addSheet': {'properties': {'title': title}}}]}
            service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id, body=body).execute()
        except Exception as e:
            if "already exists" in str(e):
                log.info("sheets.sheet_exists", title=title)
            else:
                log.error("sheets.create_failed", error=str(e))
                raise

    def update_values(self, values: list[list[Any]], range_name: str) -> None:
        """
        Safe-write a range with a 2D list of values.

        Pattern: scan existing  prepare  re-scan  merge custom rows  write.
        Any rows already in the sheet whose key (column A) does not appear in
        the incoming values are treated as user-added and appended below the
        managed data so they are never silently erased.
        """
        if not self.spreadsheet_id:
            return
        log.info("sheets.update_values", range=range_name, rows=len(values))

        def _read_range(service, range_name):
            try:
                result = service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id, range=range_name
                ).execute()
                return result.get("values", [])
            except Exception:
                return []

        def _extract_custom(existing, managed_keys, key_col=0):
            custom = []
            for row in existing[1:]:         # skip header
                if not row:
                    continue
                key = row[key_col].strip() if len(row) > key_col else ""
                if not key or key in managed_keys:
                    continue
                custom.append(row)
            return custom

        try:
            import time
            service = self._get_service()

            # SCAN 1
            scan_1 = _read_range(service, range_name)
            log.info("sheets.scan1", range=range_name, rows=len(scan_1))

            managed_keys = {str(r[0]).strip() for r in values[1:] if r} if len(values) > 1 else set()
            custom_1 = _extract_custom(scan_1, managed_keys)

            # Brief pause before scan 2
            time.sleep(0.5)

            # SCAN 2  catch any edits made while we were preparing
            scan_2 = _read_range(service, range_name)
            log.info("sheets.scan2", range=range_name, rows=len(scan_2))
            custom_2 = _extract_custom(scan_2, managed_keys)

            # Merge custom rows from both scans (deduplicated)
            seen = {r[0].strip() for r in custom_1 if r}
            for row in custom_2:
                key = row[0].strip() if row else ""
                if key and key not in seen:
                    seen.add(key)
                    custom_1.append(row)

            # Build final payload
            final_values = list(values)
            if custom_1:
                final_values.append([" USER-ADDED ROWS "])
                final_values.extend(custom_1)
                log.info("sheets.preserving_custom_rows", count=len(custom_1))

            body = {"values": final_values}
            service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body,
            ).execute()

        except Exception as e:
            log.error("sheets.update_failed", error=str(e))
            raise



# 
# Substack
# 

class SubstackClient:
    """
    Fetch posts and content from a Substack publication.
    Uses the public API endpoints.
    """

    def __init__(
        self,
        publication_url: Optional[str] = None,
        cookie: Optional[str] = None,
    ) -> None:
        url = publication_url or os.environ.get("SUBSTACK_PUBLICATION_URL", "")
        self.publication_url = url.rstrip('/')
        self.cookie = cookie or os.environ.get("SUBSTACK_COOKIE", "")

    def fetch_latest_posts(self, limit: int = 10) -> list[dict]:
        """
        Fetch the most recent posts from the publication via public API.
        """
        api_url = f"{self.publication_url}/api/v1/posts"
        params = {"limit": limit, "offset": 0, "sort": "new"}
        
        log.info("substack.fetch_latest_posts", url=api_url, limit=limit)
        
        headers = {}
        if self.cookie:
            headers["Cookie"] = self.cookie

        try:
            with httpx.Client(follow_redirects=True) as client:
                response = client.get(api_url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                # Substack API typically returns a list of post objects
                return data
        except Exception as e:
            log.error("substack.fetch_failed", error=str(e))
            raise

    def fetch_post_by_slug(self, slug: str) -> dict:
        """
        Fetch a single post's metadata and content.
        Note: Content might be truncated for public requests.
        """
        api_url = f"{self.publication_url}/api/v1/posts/{slug}"
        log.info("substack.fetch_post_by_slug", slug=slug)
        
        try:
            with httpx.Client(follow_redirects=True) as client:
                response = client.get(api_url)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            log.error("substack.fetch_post_failed", slug=slug, error=str(e))
            raise


# 
# OneDrive
# 

class OneDriveClient:
    """
    Read files from Microsoft OneDrive via Microsoft Graph API.
    """

    def __init__(self) -> None:
        pass

    def read_file(self, item_path: str) -> str:
        log.info("onedrive.read_file", path=item_path, stub=True)
        raise NotImplementedError("OneDriveClient.read_file not yet implemented")

    def list_folder(self, folder_path: str) -> list[dict]:
        log.info("onedrive.list_folder", path=folder_path, stub=True)
        raise NotImplementedError("OneDriveClient.list_folder not yet implemented")


# 
# Bluesky (Read / Fetch)
# 

class BlueSkyReader:
    """
    Fetch posts and feeds from Bluesky / AT Protocol.
    """

    def __init__(self) -> None:
        self.handle = os.environ.get("BLUESKY_HANDLE", "")
        self.app_password = os.environ.get("BLUESKY_APP_PASSWORD", "")
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from atproto import Client
            self._client = Client()
            self._client.login(self.handle, self.app_password)
        return self._client

    def fetch_feed(self, limit: int = 20) -> list[dict]:
        client = self._get_client()
        log.info("bluesky.fetch_feed", limit=limit)
        timeline = client.get_timeline(limit=limit)
        return [{"text": post.post.record.text, "uri": post.post.uri} for post in timeline.feed]

    def fetch_author_feed(self, handle: Optional[str] = None, limit: int = 20) -> list[dict]:
        client = self._get_client()
        handle = handle or self.handle
        log.info("bluesky.fetch_author_feed", handle=handle, limit=limit)
        feed = client.get_author_feed(actor=handle, limit=limit)
        return [{"text": post.post.record.text, "uri": post.post.uri, "cid": post.post.cid} for post in feed.feed]


# 
# Autonomous Systems Website (Carrd)
# 

class CarrdClient:
    """
    Fetch content from the official Carrd website.
    """
    def __init__(self, url: str = "https://systems-hub.example.com/") -> None:
        self.url = url

    def fetch_brand_pillars(self) -> dict:
        """
        Return the core mission pillars from the website.
        """
        return {
            "Community": "Building legacy through Fellowship and shared goals.",
            "Environment": "Sustainable practices and intentional growth.",
            "Transparency": "Openness to public scrutiny and process clarity."
        }
