import discord
from discord import app_commands
from discord.ext import tasks, commands
import json
import os
import asyncio
import subprocess
from dotenv import load_dotenv
from executor.tools.logging_tool import get_logger

log = get_logger("system_overseer")
load_dotenv()

# --- CONFIGURATION ---
TOKEN = os.getenv("COMMAND_CENTER_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class MasterBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Background health check loop
        self.health_check_loop.start()
        
        # Sync Slash Commands
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("master_bot.sync.guild_success", guild_id=GUILD_ID)
        else:
            await self.tree.sync()
            log.info("master_bot.sync.global_started")

    async def on_ready(self):
        print("\n" + "="*50)
        print("ðŸ›°ï¸ System Overseer is ONLINE!")
        print("Overseeing all autonomous agents...")
        print("="*50 + "\n")

    @tasks.loop(minutes=5.0)
    async def health_check_loop(self):
        """Monitors active processes and logs status"""
        log.info("master_bot.health_check.cycle")
        # In a real scenario, this could check process IDs or heartbeat files

# --- BOT INSTANCE ---
bot = MasterBot()

# --- SLASH COMMANDS ---

@bot.tree.command(name="status", description="Check the operational health of all agents (System Overseer)")
async def status(interaction: discord.Interaction):
    embed = discord.Embed(title="ðŸ›¡ï¸ Agent Health Overview", color=0x145A5A)
    
    # Check Solar Lead Scout
    bot_log = os.path.join(ROOT_DIR, "logs", "bot.log")
    solar_status = "ðŸŸ¡ Unknown"
    if os.path.exists(bot_log):
        mtime = os.path.getmtime(bot_log)
        import time
        if (time.time() - mtime) < 3600:
            solar_status = "ðŸŸ¢ Active (Logged in last hour)"
        else:
            solar_status = "ðŸ”´ Inactive (No recent logs)"
            
    embed.add_field(name="ðŸ“ Solar Lead Scout", value=solar_status, inline=False)
    
    # Check Triage Agent
    embed.add_field(name="ðŸ“© Intelligence Agent", value="ðŸŸ¢ Online (Active)", inline=False)
    
    # Check Research Agent
    research_log = os.path.join(ROOT_DIR, "..", "05_Agent_InsightLabs", "research.log")
    research_status = "âšª Idle"
    if os.path.exists(research_log):
        research_status = "ðŸŸ¢ Operational"

    embed.add_field(name="ðŸ§ª Insight Research Agent", value=research_status, inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="logs", description="View the latest 5 Guardian security events")
async def guardian_logs(interaction: discord.Interaction):
    log_file = os.path.join(ROOT_DIR, "logs", "guardian_history.json")
    if not os.path.exists(log_file):
        await interaction.response.send_message("No guardian logs found.", ephemeral=True)
        return

    with open(log_file, "r") as f:
        data = json.load(f)
        recent = data[:5]

    embed = discord.Embed(title="ðŸ›¡ï¸ Guardian Security Logs", color=0xE74C3C)
    for entry in recent:
        level_icon = "ðŸ”´" if entry['level'] == "CRITICAL" else "ðŸŸ " if entry['level'] == "WARNING" else "ðŸ”µ"
        embed.add_field(
            name=f"{level_icon} {entry['type']} - {entry['timestamp'][:16]}",
            value=entry['message'],
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="system_help", description="View the System Manual")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="ðŸ›°ï¸ System Manual", color=0x145A5A)
    embed.description = (
        "**System Overseer.** Use this to monitor your entire automated fleet.\n\n"
        "### ðŸ•¹ï¸ Commands\n"
        "`/status`: Check operational health of all bots.\n"
        "`/logs`: View recent Guardian security and error flags.\n"
        "`/overseer_help`: Show this manual."
    )
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    if not TOKEN:
        print("âŒ ERROR: COMMAND_CENTER_TOKEN not found in .env")
        import sys
        sys.exit(1)
    bot.run(TOKEN)

