import os
import subprocess
import sys

def create_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def init_project(name):
    print(f"ðŸš€ Initializing new project: {name}...")
    
    # 1. Create Directory
    if os.path.exists(name):
        print(f"âŒ Error: Directory '{name}' already exists.")
        return
    os.makedirs(name)
    os.chdir(name)

    # 2. Initialize Git
    subprocess.run(["git", "init"], capture_output=True)

    # 3. Create Standard README.md
    readme_content = f"""# ðŸš€ {name}

A new Autonomous Systems project component.

---

## ðŸŒŸ Features
- Feature 1
- Feature 2

## ðŸ› ï¸ Setup & Installation
```bash
# Example setup commands
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## ðŸ“‚ Project Structure
- `main.py`: Entry point.
- `.env.example`: Configuration template.
"""
    create_file("README.md", readme_content)

    # 4. Create Security .gitignore
    gitignore_content = """# Standard Privacy Filter
.env
credentials.json
token.json
google-sheets_auth
*.token
*.key
*.pem
.venv/
__pycache__/
logs/
drafts/
node_modules/
.DS_Store
"""
    create_file(".gitignore", gitignore_content)

    # 5. Create .env.example
    create_file(".env.example", "# Project Config Template\nDISCORD_BOT_TOKEN=\nDISCORD_SECURITY_WEBHOOK_URL=")

    # 6. Create Boilerplate main.py
    main_py_content = """import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Import Guardian logic (assume flat structure or correct symlinks)
# In real usage, you'd add the Core path to sys.path here.

@bot.event
async def on_ready():
    print(f"âœ… {name} is online!")

@bot.command()
async def stop(ctx):
    if await bot.is_owner(ctx.author):
        await ctx.send("ðŸ›‘ Shutting down...")
        await bot.close()
        sys.exit(0)
    else:
        await ctx.send("â›” Access Denied.")

if __name__ == '__main__':
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Set DISCORD_BOT_TOKEN in .env")
"""
    create_file("main.py", main_py_content)

    # 7. Install Pre-Commit Hook (Corrected path for 04_Agent_Core)
    hook_dir = os.path.join(".git", "hooks")
    os.makedirs(hook_dir, exist_ok=True)
    hook_path = os.path.join(hook_dir, "pre-commit")
    
    # Path is now relative to the project folder
    hook_content = "#!/bin/sh\npython ../04_Agent_Core/scripts/check_secrets.py"
    create_file(hook_path, hook_content)

    print(f"âœ… Success! Project '{name}' is ready with README, security filters, and git hooks.")
    print(f"ðŸ”— Next: cd {name} to start building.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/new_project.py <project_name>")
    else:
        init_project(sys.argv[1])

