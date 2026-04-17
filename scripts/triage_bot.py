import discord
from discord import app_commands
from discord.ext import tasks, commands
import json
import os
import asyncio
from dotenv import load_dotenv

# Import our existing Agent stack
from executor.tools.email import EmailClient
from executor.tools.transformation import OpenAIClient
from executor.tools.messaging import MessagingClient
from executor.tools.history import TriageHistory
from orchestrator.email_triage import EmailTriageOrchestrator
from executor.tools.logging_tool import get_logger

log = get_logger("Agent_analyst")
load_dotenv()

# --- CONFIGURATION ---
CONFIG_PATH = "data/config.json"
TOKEN = os.getenv("TRIAGE_BOT_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")

class TriageBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.orchestrator = None
        self.last_run_stats = "No cycles run yet."

    async def setup_hook(self):
        # Initialize the Orchestrator
        self.reload_orchestrator()
        # Start the background triage loop
        self.triage_loop.start()
        # INSTANT SYNC: Target the specific server for zero propagation delay
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("bot.sync.guild_success", guild_id=GUILD_ID)
        else:
            # Global sync fallback (slower)
            await self.tree.sync()
            log.info("bot.sync.global_started")

    async def on_ready(self):
        print("\n" + "="*50)
        print(" Intelligence Agent is ONLINE!")
        print("Connected to Discord and listening for triage commands.")
        print("="*50 + "\n")

    def reload_orchestrator(self):
        """Loads/Reloads the orchestrator with current config.json"""
        if not os.path.exists(CONFIG_PATH):
            return

        with open(CONFIG_PATH, "r") as f:
            c = json.load(f)
            
        email = EmailClient(
            imap_server=c.get("imap_server", "imap.gmail.com"),
            smtp_server="smtp.gmail.com",
            email_user=c.get("email_user", ""),
            email_pass=c.get("email_pass", "")
        )
        
        # Messaging is handled internally by the bot in this version
        messaging = MessagingClient(webhook_url=c.get("msg_url", ""), provider=c.get("msg_provider", "discord"))
        history = TriageHistory()
        
        self.orchestrator = EmailTriageOrchestrator(email, OpenAIClient(), messaging, history)

    @tasks.loop(minutes=15.0)
    async def triage_loop(self):
        """Standard 15-minute background sweep"""
        log.info("bot.triage_loop.start")
        await self.run_triage_cycle()

    async def run_triage_cycle(self, ignore_history: bool = False, interaction: discord.Interaction = None):
        """Performs a single triage sweep with live progress updates."""
        if not self.orchestrator:
            return 0

        # Defer immediately to show "Thinking..."
        if interaction and not interaction.response.is_done():
            await interaction.response.defer()

        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)

        rules = {
            "business_goal": config.get("goal", ""),
            "vips": config.get("vips", ""),
            "urgency_triggers": config.get("urgency", ""),
            "tone": config.get("tone", "Professional"),
            "threshold": config.get("threshold", 4)
        }

        # Progress Handler: Updates Discord message every 5 emails
        async def progress_hook(current, total):
            if interaction and (current == 1 or current % 5 == 0 or current == total):
                status_msg = f" **Triaging email {current} of {total}...** (This takes a moment)"
                await interaction.edit_original_response(content=status_msg)

        # Run the now-async orchestrator logic
        results = await self.orchestrator.run_triage(
            rules, 
            use_management=config.get("enable_filing", False),
            folders=["INBOX", "[Gmail]/Spam"],
            ignore_history=ignore_history,
            progress_callback=progress_hook if interaction else None
        )

        self.last_run_stats = f"Last Sweep: {len(results)} items triaged."
        return len(results)

# --- INTERACTIVE COMPONENTS ---

class SensitivitySelect(discord.ui.Select):
    def __init__(self, current_val):
        options = [
            discord.SelectOption(label="Low (Notify on Level 3+)", value="3", description="More alerts, safe for standard operation."),
            discord.SelectOption(label="Strict (Notify on Level 4+)", value="4", description="Standard high-signal filtering."),
            discord.SelectOption(label="Emergency (Level 5 Only)", value="5", description="Only alert on critical business failures.")
        ]
        super().__init__(placeholder=f"Sensitivity: {current_val}", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        config["threshold"] = int(self.values[0])
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=4)
        await interaction.response.send_message(f" **Notification Sensitivity set to:** {self.values[0]}+", ephemeral=True)

class ToneSelect(discord.ui.Select):
    def __init__(self, current_val):
        options = [
            discord.SelectOption(label="Professional", value="Professional"),
            discord.SelectOption(label="Concise", value="Concise"),
            discord.SelectOption(label="Casual", value="Casual")
        ]
        super().__init__(placeholder=f"Tone: {current_val}", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        config["tone"] = self.values[0]
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=4)
        await interaction.response.send_message(f" **AI Tone updated to:** {self.values[0]}", ephemeral=True)

class VIPModal(discord.ui.Modal, title='Manage VIP List'):
    vips = discord.ui.TextInput(label='VIP Email List (Comma separated)', style=discord.TextStyle.long, placeholder='ceo@company.com, client1@partner.com', required=True)

    async def on_submit(self, interaction: discord.Interaction):
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        config["vips"] = self.vips.value
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=4)
        await interaction.response.send_message(f" **VIP List Updated!**", ephemeral=True)

class UrgencyModal(discord.ui.Modal, title='Manage Urgency Triggers'):
    triggers = discord.ui.TextInput(label='Urgency Triggers (Keywords)', style=discord.TextStyle.long, placeholder='invoice, backstabbr, payment, deadline', required=True)

    async def on_submit(self, interaction: discord.Interaction):
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        config["urgency"] = self.triggers.value
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=4)
        
        # Reload orchestrator to catch changes
        bot.reload_orchestrator()
        
        view = RescanView(bot)
        await interaction.response.send_message(f" **Urgency Triggers Updated!**", view=view)

class SettingsView(discord.ui.View):
    def __init__(self, config):
        super().__init__(timeout=None)
        self.add_item(SensitivitySelect(config.get("threshold", 4)))
        self.add_item(ToneSelect(config.get("tone", "Professional")))

    @discord.ui.button(label=" Toggle Auto-Filing", style=discord.ButtonStyle.secondary)
    async def toggle_filing(self, interaction: discord.Interaction, button: discord.ui.Button):
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        config["enable_filing"] = not config.get("enable_filing", False)
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=4)
        button.label = f" Auto-Filing: {'ON' if config['enable_filing'] else 'OFF'}"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label=" Update VIPs", style=discord.ButtonStyle.secondary)
    async def update_vips(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VIPModal())

    @discord.ui.button(label=" Manage Triggers", style=discord.ButtonStyle.secondary)
    async def manage_triggers(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UrgencyModal())

class RescanView(discord.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=60)
        self.bot = bot_instance

    @discord.ui.button(label=" Re-Scan Latest Emails", style=discord.ButtonStyle.primary)
    async def rescan_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        count = await self.bot.run_triage_cycle(ignore_history=True, interaction=interaction)
        await interaction.edit_original_response(
            content=f" **Deep Sweep Complete.** Found {count} items that match your new rules."
        )
        self.stop()

bot = TriageBot()

# --- SLASH COMMANDS ---

@bot.tree.command(name="settings", description="Open the Agent Control Panel")
async def settings(interaction: discord.Interaction):
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
        
    embed = discord.Embed(title=" Intelligence Agent : Control Panel", description="Manage your analyst's behavior and sensitivity here.", color=0x3498DB)
    embed.add_field(name="Current Goal", value=f"_{config.get('goal', 'None')}_", inline=False)
    
    triggers = config.get("urgency", "None").split(',')
    trigger_list = "\n".join([f" {t.strip()}" for t in triggers if t.strip()])
    embed.add_field(name=" Active Urgency Triggers", value=trigger_list or "None", inline=False)
    
    embed.add_field(name="Notification Mode", value=f"Level {config.get('threshold', 4)}+", inline=True)
    embed.add_field(name="Draft Tone", value=config.get("tone", "Professional"), inline=True)
    embed.add_field(name="Auto-Filing", value="Active" if config.get("enable_filing") else "Inactive", inline=True)
    
    view = SettingsView(config)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="analyst_help", description="View the Agent Manual")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title=" Intelligence Agent Manual", color=0x3498DB)
    embed.description = (
        "**Welcome to the Intelligence Agent Office.** Here is how to control your agent:\n\n"
        "###  Commands\n"
        "`/settings`: Open the triage dashboard (Sensitivity, Tone, Filing).\n"
        "`/goal`: Update your current business priorities.\n"
        "`/urgency`: Add keywords that trigger emergency alerts.\n"
        "`/sweep`: Force a manual scan of Inbox & Spam.\n"
        "`/status`: View analyst health and recent activity.\n\n"
        "###  Features\n"
        "**Deep Sweep:** Use the [ Re-Scan] button to check history after updating rules.\n"
        "**VIP Bypass:** Ensure key client emails never get filtered."
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="goal", description="Update the business goal / focus for triage")
async def update_goal(interaction: discord.Interaction, new_goal: str):
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    config["goal"] = new_goal
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)
    bot.reload_orchestrator()
    view = RescanView(bot)
    await interaction.response.send_message(f" **Business Goal Updated:** {new_goal}", view=view)

@bot.tree.command(name="urgency", description="Update high-priority urgency triggers")
async def update_urgency(interaction: discord.Interaction, triggers: str):
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    config["urgency"] = triggers
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)
    bot.reload_orchestrator()
    view = RescanView(bot)
    await interaction.response.send_message(f" **Urgency Triggers Updated:** {triggers}", view=view)

@bot.tree.command(name="sweep", description="Force an immediate triage sweep (Inbox + Spam)")
async def sweep(interaction: discord.Interaction, rescan_latest: bool = False):
    count = await bot.run_triage_cycle(ignore_history=rescan_latest, interaction=interaction)
    await interaction.edit_original_response(content=f" **Sweep Complete.** Processed {count} items.")

if __name__ == "__main__":
    if not TOKEN:
        print(" ERROR: TRIAGE_BOT_TOKEN not found in .env")
        sys.exit(1)
    bot.run(TOKEN)
