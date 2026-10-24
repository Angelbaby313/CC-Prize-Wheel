import os, json, random, asyncio
from datetime import datetime, timezone
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
DATA_FILE = os.getenv("DATA_FILE", "wheel_data.json")
CHIRAQ_ALLOWED_ROLE_IDS = {
    1553198437267152966,
    1553162974162849812,
    1553198442023747656,
}

DEFAULT_PRIZES = [
    "Donor Car", "$5,000 Cash", "$5,000 Cash", "$2,500 Cash",
    "Air Soft Gun", "Melee Weapon", "Legal Item Pack", "Illegal Item Pack"
]

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, dict) and "guilds" in d:
                    return d
        except Exception:
            pass
    return {"guilds": {}}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

data = load_data()

def guild_config(guild_id):
    gid = str(guild_id)
    if gid not in data["guilds"]:
        data["guilds"][gid] = {
            "prizes": DEFAULT_PRIZES.copy(),
            "log_channel_id": 0,
            "manager_role_id": 0,
            "spins": []
        }
        save_data()
    return data["guilds"][gid]

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

def is_manager(member, cfg):
    if member.guild_permissions.administrator:
        return True
    member_role_ids = {r.id for r in member.roles}
    if member_role_ids & CHIRAQ_ALLOWED_ROLE_IDS:
        return True
    role_id = int(cfg.get("manager_role_id", 0) or 0)
    return bool(role_id and role_id in member_role_ids)

def prize_emoji(p):
    q = p.lower()
    if "car" in q: return "🚗"
    if "cash" in q or "$" in q: return "💵"
    if "air" in q: return "🎯"
    if "melee" in q: return "🥊"
    if "pack" in q: return "📦"
    return "🎁"

class SpinView(discord.ui.View):
    def __init__(self, guild_id, winner_id, started_by_id):
        super().__init__(timeout=3600)
        self.guild_id = guild_id
        self.winner_id = winner_id
        self.started_by_id = started_by_id
        self.used = False

    @discord.ui.button(label="SPIN THE WHEEL", emoji="🎡", style=discord.ButtonStyle.danger)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.winner_id:
            return await interaction.response.send_message(
                "This prize wheel belongs to the selected winner. 💕", ephemeral=True
            )
        if self.used:
            return await interaction.response.send_message("This wheel has already been spun.", ephemeral=True)

        cfg = guild_config(self.guild_id)
        prizes = cfg.get("prizes") or DEFAULT_PRIZES
        self.used = True
        button.disabled = True
        await interaction.response.edit_message(view=self)

        chosen = random.choice(prizes)
        for t in ["🎡 Spinning .", "🎡 Spinning . .", "🎡 Spinning . . .", "🎰 Slowing down..."]:
            e = discord.Embed(
                title="🎡 CHIRAQ CHRONICLES PRIZE WHEEL",
                description=f"## {t}",
                color=discord.Color.red()
            )
            e.add_field(name="Winner", value=interaction.user.mention, inline=False)
            await interaction.message.edit(embed=e, view=self)
            await asyncio.sleep(0.9)

        e = discord.Embed(
            title="🎡 CHIRAQ CHRONICLES PRIZE WHEEL",
            description=f"# 🎉 YOU WON!\n## {prize_emoji(chosen)} **{chosen}**",
            color=discord.Color.gold()
        )
        e.add_field(name="Winner", value=interaction.user.mention, inline=False)
        e.add_field(
            name="Prize Delivery",
            value="Please let staff know your **City ID #** so your prize can be delivered.",
            inline=False
        )
        e.set_footer(text="Chiraq Chronicles • WIN BIG")
        await interaction.message.edit(embed=e, view=self)

        cfg["spins"].append({
            "winner_id": interaction.user.id,
            "winner": str(interaction.user),
            "prize": chosen,
            "started_by_id": self.started_by_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        save_data()

        log_id = int(cfg.get("log_channel_id", 0) or 0)
        if log_id:
            ch = interaction.guild.get_channel(log_id)
            if ch:
                le = discord.Embed(title="🎡 Prize Wheel Log", color=discord.Color.dark_red())
                le.add_field(name="Winner", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
                le.add_field(name="Prize", value=f"{prize_emoji(chosen)} {chosen}", inline=False)
                le.add_field(name="City ID", value="Awaiting winner/staff confirmation", inline=False)
                le.add_field(name="Started By", value=f"<@{self.started_by_id}>", inline=False)
                await ch.send(embed=le)

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
    except Exception as e:
        print("sync error", e)
    print(f"Logged in as {bot.user} | {len(bot.guilds)} server(s)")

@bot.tree.command(name="ticket_wheel_setup", description="Administrator: configure ticket Prize Wheel")
@app_commands.describe(
    log_channel="Private channel for prize logs",
    manager_role="Role allowed to manage and start the wheel"
)
async def ticket_wheel_setup(interaction: discord.Interaction, log_channel: discord.TextChannel,
                      manager_role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Server Administrator only.", ephemeral=True)
    cfg = guild_config(interaction.guild_id)
    cfg["log_channel_id"] = log_channel.id
    cfg["manager_role_id"] = manager_role.id
    save_data()
    await interaction.response.send_message(
        f"✅ Prize Wheel configured for **{interaction.guild.name}**.\n"
        f"🎟️ Spins can be started inside winner ticket channels.\n"
        f"🧾 Logs: {log_channel.mention}\n"
        f"👑 Manager role: {manager_role.mention}",
        ephemeral=True
    )

@bot.tree.command(name="prizewheel", description="Start the Prize Wheel for a winner")
@app_commands.describe(winner="The winner who gets to spin")
async def prizewheel(interaction: discord.Interaction, winner: discord.Member):
    cfg = guild_config(interaction.guild_id)
    if not is_manager(interaction.user, cfg):
        return await interaction.response.send_message("You do not have permission to start a prize wheel.", ephemeral=True)
    e = discord.Embed(
        title="🎡 CHIRAQ CHRONICLES PRIZE WHEEL",
        description=f"### Congratulations {winner.mention}!\n"
                    "You earned a spin on the **Chiraq Chronicles Prize Wheel**.\n\n"
                    "Press the button below when you’re ready. Everyone will see what you win! 🎉",
        color=discord.Color.red()
    )
    e.add_field(
        name="HOW IT WORKS",
        value="**1.** Staff selects the winner\n"
              "**2.** Winner presses the Spin button\n"
              "**3.** Prize is displayed for everyone to see\n"
              "**4.** Let staff know your **City ID #** so your prize can be delivered",
        inline=False
    )
    e.set_footer(text="Only the selected winner can spin • One spin per wheel")
    await interaction.response.send_message(
        embed=e, view=SpinView(interaction.guild_id, winner.id, interaction.user.id)
    )

@bot.tree.command(name="prize_list", description="View this server's Prize Wheel slots")
async def prize_list(interaction: discord.Interaction):
    cfg = guild_config(interaction.guild_id)
    lines = [f"**{i+1}.** {prize_emoji(p)} {p}" for i, p in enumerate(cfg.get("prizes", []))]
    await interaction.response.send_message(
        embed=discord.Embed(
            title="🎡 Current Prize Wheel",
            description="\n".join(lines) or "No prizes configured.",
            color=discord.Color.red()
        ),
        ephemeral=True
    )

@bot.tree.command(name="prize_add", description="Prize manager: add a prize slot")
@app_commands.describe(prize="Prize name to add")
async def prize_add(interaction: discord.Interaction, prize: str):
    cfg = guild_config(interaction.guild_id)
    if not is_manager(interaction.user, cfg):
        return await interaction.response.send_message("Prize manager only.", ephemeral=True)
    prize = prize.strip()[:80]
    if not prize:
        return await interaction.response.send_message("Enter a prize name.", ephemeral=True)
    cfg["prizes"].append(prize)
    save_data()
    await interaction.response.send_message(
        f"✅ Added **{prize}**. Duplicate slots increase that prize's odds.", ephemeral=True
    )

@bot.tree.command(name="prize_remove", description="Prize manager: remove one matching prize slot")
@app_commands.describe(prize="Exact prize name to remove")
async def prize_remove(interaction: discord.Interaction, prize: str):
    cfg = guild_config(interaction.guild_id)
    if not is_manager(interaction.user, cfg):
        return await interaction.response.send_message("Prize manager only.", ephemeral=True)
    matches = [p for p in cfg["prizes"] if p.lower() == prize.strip().lower()]
    if not matches:
        return await interaction.response.send_message(
            "I could not find that exact prize. Use `/prize_list` first.", ephemeral=True
        )
    cfg["prizes"].remove(matches[0])
    save_data()
    await interaction.response.send_message(f"🗑️ Removed one **{matches[0]}** slot.", ephemeral=True)

@bot.tree.command(name="prize_reset", description="Prize manager: reset this server to the original 8 slots")
async def prize_reset(interaction: discord.Interaction):
    cfg = guild_config(interaction.guild_id)
    if not is_manager(interaction.user, cfg):
        return await interaction.response.send_message("Prize manager only.", ephemeral=True)
    cfg["prizes"] = DEFAULT_PRIZES.copy()
    save_data()
    await interaction.response.send_message(
        "♻️ This server's Prize Wheel was reset to the original 8 slots.", ephemeral=True
    )

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is required.")
bot.run(TOKEN)
