import discord
from discord.ext import commands
import asyncio

INTENTS = discord.Intents.default()
INTENTS.guilds = True
INTENTS.members = True  # required to iterate guild members

bot = commands.Bot(command_prefix="!", intents=INTENTS)

@bot.command()
@commands.has_permissions(administrator=True)
async def resetserver(ctx, new_name: str, new_channel_name: str, icon_path: str = None):
    """
    Usage: !resetserver "New Server Name" "channel-name" path/to/icon.png
    Deletes all channels, bans every bannable member, renames the server,
    sets a new icon, and creates 20 channels with the given name.
    """
    guild = ctx.guild

    # --- Confirmation gate ---
    await ctx.send(
        f"⚠️ This will **delete every channel**, **ban every member** I'm able to, "
        f"rename the server to `{new_name}`, and recreate 20 channels named `{new_channel_name}`.\n"
        f"Type `CONFIRM` within 30 seconds to proceed."
    )

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content == "CONFIRM"

    try:
        await bot.wait_for("message", check=check, timeout=30)
    except asyncio.TimeoutError:
        await ctx.send("Reset cancelled (no confirmation received).")
        return

    await ctx.send(f"Starting reset on **{guild.name}**... this cannot be undone.")

    # 1. Delete all channels
    for channel in list(guild.channels):
        try:
            await channel.delete(reason="Server reset requested")
            await asyncio.sleep(1)
        except discord.Forbidden:
            print(f"Missing permission to delete {channel.name}")
        except discord.HTTPException as e:
            print(f"Failed to delete {channel.name}: {e}")

    # 2. Ban every member the bot is able to ban
    me = guild.me
    banned, failed = [], []
    for member in list(guild.members):
        if member == bot.user or member == ctx.author:
            continue  # don't ban the bot itself or whoever ran the command
        if member.top_role >= me.top_role or member == guild.owner:
            failed.append(member)  # role hierarchy will block this anyway
            continue
        try:
            await guild.ban(member, reason="Server reset requested", delete_message_days=0)
            banned.append(member)
            await asyncio.sleep(1)
        except discord.Forbidden:
            failed.append(member)
        except discord.HTTPException as e:
            print(f"Failed to ban {member}: {e}")
            failed.append(member)

    print(f"Banned {len(banned)} members, could not ban {len(failed)}")

    # 3. Rename the server
    try:
        await guild.edit(name=new_name, reason="Server reset")
    except discord.HTTPException as e:
        print(f"Failed to rename server: {e}")

    # 4. Set new server icon
    if icon_path:
        try:
            with open(icon_path, "rb") as f:
                icon_bytes = f.read()
            await guild.edit(icon=icon_bytes, reason="Server reset")
        except FileNotFoundError:
            print(f"Icon file not found: {icon_path}")
        except discord.HTTPException as e:
            print(f"Failed to set icon: {e}")

    # 5. Create 20 channels with the same name
    created = []
    for i in range(20):
        try:
            ch = await guild.create_text_channel(new_channel_name, reason="Server reset")
            created.append(ch)
            await asyncio.sleep(1)
        except discord.HTTPException as e:
            print(f"Failed to create channel #{i+1}: {e}")

    if created:
        await created[0].send(
            f"✅ Reset complete. Banned {len(banned)} members ({len(failed)} could not be banned — "
            f"likely due to role hierarchy). Created {len(created)} channels named `{new_channel_name}`."
        )

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run("YOUR_BOT_TOKEN")