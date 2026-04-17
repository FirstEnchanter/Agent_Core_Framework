import os
import re
import sys

# Common patterns for secrets
PATTERNS = {
    "Discord Bot Token": r"MT[A-Za-z0-9+/=]{22,}\.[A-Za-z0-9-_]{6,}\.[A-Za-z0-9-_]{27,}",
    "GitHub PAT": r"ghp_[A-Za-z0-9]{36,}",
    "OpenAI API Key": r"sk-[A-Za-z0-9]{48,}",
    "Google Client ID": r"[0-9]+-[A-Za-z0-9_]+\.apps\.googleusercontent\.com",
    "Private Key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "Apify API Token": r"apify_api_[A-Za-z0-9]{36,}",
}

GITHUB_IGNORED_DIRS  = [".git", ".venv", "__pycache__", "node_modules", "logs", "drafts"]
GITHUB_IGNORED_FILES = ["credentials.json", "token.json", "google-sheets_auth", ".env"]

def scan_file(filepath):
    """Scans a single file for secret patterns."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            for name, pattern in PATTERNS.items():
                if re.search(pattern, content):
                    return name, pattern
    except Exception as e:
        print(f"  [Error reading] {filepath}: {e}")
    return None, None

def main():
    print("Locked & Loaded: Scanning Agent Workspace for Secrets...")
    print("-" * 50)
    
    found_any = False
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    for root, dirs, files in os.walk(root_dir):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in GITHUB_IGNORED_DIRS]
        
        for file in files:
            # Skip ignored files
            if file in GITHUB_IGNORED_FILES or file.endswith((".png", ".jpg", ".pdf", ".exe", ".bin", ".log")):
                continue
            if file == "check_secrets.py" or file == "SECURITY_SOP.md":
                continue
            
            filepath = os.path.join(root, file)
            match_name, _ = scan_file(filepath)
            if match_name:
                rel_path = os.path.relpath(filepath, root_dir)
                print(f"!!! [LEAK DETECTED] {match_name} found in: {rel_path}")
                
                # Report to Guardian
                try:
                    import guardian
                    guardian.report_leak(match_name, rel_path)
                except ImportError:
                    pass
                
                found_any = True

    print("-" * 50)
    if found_any:
        print("[X] SECURITY CHECK FAILED: Do not commit until the above leaks are removed.")
        sys.exit(1)
    else:
        print("[V] SECURITY CHECK PASSED: No hardcoded secrets found.")
        sys.exit(0)

if __name__ == "__main__":
    main()

