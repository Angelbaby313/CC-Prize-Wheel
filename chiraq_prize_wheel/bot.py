import os, json, random, asyncio
from datetime import datetime, timezone
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', '0') or 0)
PRIZE_CHANNEL_ID = int(os.getenv('PRIZE_CHANNEL_ID', '0') or 0)
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', '0') or 0)
MANAGER_ROLE_NAMES = [x.strip() for x in os.getenv('MANAGER_ROLE_NAMES','Admin,Head of Staff,Head Management').split(',') if x.strip()]
STAFF_ROLE_NAMES = [x.strip() for x in os.getenv('STAFF_ROLE_NAMES','Admin,Head of Staff,Head Management,Trial Mod,Moderator').split(',') if x.strip()]
DATA_FILE = os.getenv('DATA_FILE','wheel_data.json')
DEFAULT_PRIZES = ['Donor Car','$5,000 Cash','$5,000 Cash','$2,500 Cash','Air Soft Gun','Melee Weapon','Legal Item Pack','Illegal Item Pack']

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE,'r',encoding='utf-8') as f: return json.load(f)
        except Exception: pass
    return {'prizes': DEFAULT_PRIZES.copy(), 'spins': []}

def save_data(data):
    with open(DATA_FILE,'w',encoding='utf-8') as f: json.dump(data,f,indent=2)

data=load_data()
intents=discord.Intents.default(); intents.members=True
bot=commands.Bot(command_prefix='!', intents=intents)

def has_named_role(member, names):
    return member.guild_permissions.administrator or any(r.name in names for r in member.roles)

def prize_emoji(p):
    q=p.lower()
    if 'car' in q: return '🚗'
    if 'cash' in q or '$' in q: return '💵'
    if 'air' in q: return '🎯'
    if 'melee' in q: return '🥊'
    if 'illegal' in q: return '📦'
    if 'legal' in q: return '📦'
    return '🎁'

class SpinView(discord.ui.View):
    def __init__(self, winner_id, started_by_id):
        super().__init__(timeout=3600)
        self.winner_id=winner_id; self.started_by_id=started_by_id; self.used=False
    @discord.ui.button(label='SPIN THE WHEEL', emoji='🎡', style=discord.ButtonStyle.danger)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.winner_id:
            return await interaction.response.send_message('This prize wheel belongs to the selected winner. 💕', ephemeral=True)
        if self.used:
            return await interaction.response.send_message('This wheel has already been spun.', ephemeral=True)
        self.used=True; button.disabled=True
        await interaction.response.edit_message(view=self)
        prizes=data.get('prizes') or DEFAULT_PRIZES
        chosen=random.choice(prizes)
        frames=['🎡 Spinning .','🎡 Spinning . .','🎡 Spinning . . .','🎰 Slowing down...']
        for t in frames:
            e=discord.Embed(title='🎡 CHIRAQ CHRONICLES PRIZE WHEEL', description=f'## {t}', color=discord.Color.red())
            e.add_field(name='Winner', value=interaction.user.mention, inline=False)
            await interaction.message.edit(embed=e, view=self); await asyncio.sleep(0.9)
        e=discord.Embed(title='🎡 CHIRAQ CHRONICLES PRIZE WHEEL', description=f'# 🎉 YOU WON!\n## {prize_emoji(chosen)} **{chosen}**', color=discord.Color.gold())
        e.add_field(name='Winner', value=interaction.user.mention, inline=False)
        e.add_field(name='Prize Delivery', value='Please let staff know your **City ID #** so your prize can be delivered.', inline=False)
        e.set_footer(text='Chiraq Chronicles • WIN BIG')
        await interaction.message.edit(embed=e, view=self)
        record={'winner_id':interaction.user.id,'winner':str(interaction.user),'prize':chosen,'started_by_id':self.started_by_id,'timestamp':datetime.now(timezone.utc).isoformat()}
        data['spins'].append(record); save_data(data)
        if LOG_CHANNEL_ID:
            ch=interaction.guild.get_channel(LOG_CHANNEL_ID)
            if ch:
                le=discord.Embed(title='🎡 Prize Wheel Log', color=discord.Color.dark_red())
                le.add_field(name='Winner',value=f'{interaction.user.mention} (`{interaction.user.id}`)',inline=False)
                le.add_field(name='Prize',value=f'{prize_emoji(chosen)} {chosen}',inline=False)
                le.add_field(name='City ID',value='Awaiting winner/staff confirmation',inline=False)
                le.add_field(name='Started By',value=f'<@{self.started_by_id}>',inline=False)
                await ch.send(embed=le)

@bot.event
async def on_ready():
    try:
        if GUILD_ID:
            guild=discord.Object(id=GUILD_ID); bot.tree.copy_global_to(guild=guild); await bot.tree.sync(guild=guild)
        else: await bot.tree.sync()
    except Exception as e: print('sync error',e)
    print(f'Logged in as {bot.user}')

@bot.tree.command(name='prizewheel', description='Start the Chiraq Chronicles Prize Wheel for a winner')
@app_commands.describe(winner='The winner who gets to spin')
async def prizewheel(interaction: discord.Interaction, winner: discord.Member):
    if not has_named_role(interaction.user, STAFF_ROLE_NAMES):
        return await interaction.response.send_message('You do not have permission to start a prize wheel.',ephemeral=True)
    if PRIZE_CHANNEL_ID and interaction.channel_id != PRIZE_CHANNEL_ID:
        return await interaction.response.send_message(f'Please use the prize wheel in <#{PRIZE_CHANNEL_ID}>.',ephemeral=True)
    e=discord.Embed(title='🎡 CHIRAQ CHRONICLES PRIZE WHEEL', description=f'### Congratulations {winner.mention}!\nYou earned a spin on the **Chiraq Chronicles Prize Wheel**.\n\nPress the button below when you’re ready. Everyone will see what you win! 🎉', color=discord.Color.red())
    e.add_field(name='HOW IT WORKS',value='**1.** Staff selects the winner\n**2.** Winner presses the Spin button\n**3.** Prize is displayed for everyone to see\n**4.** Let staff know your **City ID #** so your prize can be delivered',inline=False)
    e.set_footer(text='Only the selected winner can spin • One spin per wheel')
    await interaction.response.send_message(embed=e,view=SpinView(winner.id,interaction.user.id))

@bot.tree.command(name='prize_list', description='View current Prize Wheel slots')
async def prize_list(interaction: discord.Interaction):
    lines=[f'**{i+1}.** {prize_emoji(p)} {p}' for i,p in enumerate(data.get('prizes',[]))]
    await interaction.response.send_message(embed=discord.Embed(title='🎡 Current Prize Wheel',description='\n'.join(lines) or 'No prizes configured.',color=discord.Color.red()),ephemeral=True)

@bot.tree.command(name='prize_add', description='Admin/Head Staff: add a prize slot')
@app_commands.describe(prize='Prize name to add')
async def prize_add(interaction: discord.Interaction, prize: str):
    if not has_named_role(interaction.user, MANAGER_ROLE_NAMES): return await interaction.response.send_message('Admin/Head Staff only.',ephemeral=True)
    prize=prize.strip()[:80]
    if not prize: return await interaction.response.send_message('Enter a prize name.',ephemeral=True)
    data['prizes'].append(prize); save_data(data)
    await interaction.response.send_message(f'✅ Added **{prize}** as a new wheel slot. Adding duplicates increases that prize’s odds.',ephemeral=True)

@bot.tree.command(name='prize_remove', description='Admin/Head Staff: remove one matching prize slot')
@app_commands.describe(prize='Exact prize name to remove')
async def prize_remove(interaction: discord.Interaction, prize: str):
    if not has_named_role(interaction.user, MANAGER_ROLE_NAMES): return await interaction.response.send_message('Admin/Head Staff only.',ephemeral=True)
    matches=[p for p in data['prizes'] if p.lower()==prize.strip().lower()]
    if not matches: return await interaction.response.send_message('I could not find that exact prize. Use `/prize_list` first.',ephemeral=True)
    data['prizes'].remove(matches[0]); save_data(data)
    await interaction.response.send_message(f'🗑️ Removed one **{matches[0]}** slot.',ephemeral=True)

@bot.tree.command(name='prize_reset', description='Admin/Head Staff: reset to original 8 prize slots')
async def prize_reset(interaction: discord.Interaction):
    if not has_named_role(interaction.user, MANAGER_ROLE_NAMES): return await interaction.response.send_message('Admin/Head Staff only.',ephemeral=True)
    data['prizes']=DEFAULT_PRIZES.copy(); save_data(data)
    await interaction.response.send_message('♻️ Prize Wheel reset to the original 8 slots.',ephemeral=True)

if not TOKEN: raise RuntimeError('DISCORD_TOKEN environment variable is required.')
bot.run(TOKEN)
