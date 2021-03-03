import os
import discord
import random
import asyncio
import json
# import traceback
from dotenv import load_dotenv
from discord.ext import commands

# Load bot token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


def create_old_file(filename):
    """
    Renames filename to filename_old. Appends numbers if filename_old exists

    :param filename: Name of the file (without extension) to process
    :return: None
    """
    newname = filename+"_old.json"
    num = 1
    while os.path.exists(newname):
        newname = filename+"_old"+str(num)+".json"
        num += 1
    os.rename(filename+".json", newname)


# Load the opt-out file
try:
    opt_out_file = open("opt_out.json", "r")
    opt_out_list = json.load(opt_out_file)
    opt_out_file.close()
except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
    opt_out_file = open("opt_out.json", "r")

    # Create it if it is missing
    if isinstance(e, FileNotFoundError):
        print("File opt_out.json not found, creating it...")

    # Recreate it if the file is bad
    elif isinstance(e, json.decoder.JSONDecodeError):
        print("WARNING: Json file corrupted, re-creating it...")
        opt_out_file.close()
        create_old_file("opt_out")

    # Initialize the opt-out file
    opt_out_file = open("opt_out.json", "w")
    json.dump([], opt_out_file)
    opt_out_file.close()
    opt_out_list = []

# client = discord.Client()
bot = commands.Bot(command_prefix='!')  # Bot object with command prefix

cooldown = []               # Per-User cooldown status
globalCooldown = False      # Global cooldown status
USE_GLOBAL_COOLDOWN = True  # Set to True to use the global cooldown
COOLDOWN_TIME = 3           # Cooldown time (seconds)
CHECK_BOOSTER_ROLE = True   # Require the users to be a booster for role rave
CHECK_OPT_OUT = True        # Check if the user opted out
ENABLE_RAVE = True          # Do the role rave shenanigans

@bot.event
async def on_ready():
    """
    Simply displays a connection message.

    :return: None
    """
    print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_message(message):
    """
    Does the role rave shenanigans.

    :param message: message
    :return: None
    """

    global cooldown
    global globalCooldown
    global ENABLE_RAVE
    member = message.author
    server = member.guild
    isCommand = False           # Set to true if message is a command
    isCooldownActive = False    # Set to true if the cooldown is active
    isOptedOut = False          # Set to true if user opted out (if applicable)
    isBooster = True            # Set to false if CHECK_BOOSTER_ROLE and if member is not a booster


    # Don't process the bot's own messages
    if member == bot.user:
        return

    # Don't progress if the role rave is turned off
    if not ENABLE_RAVE:
        return

    # Check if the message is a command
    try:
        if message.content[0] == '!':
            isCommand = True
    except:
        pass

    # Check if the cooldown is active
    if USE_GLOBAL_COOLDOWN:
        isCooldownActive = globalCooldown
    else:
        if member.id in cooldown:
            isCooldownActive = True

    # Check for booster role
    if CHECK_BOOSTER_ROLE:
        isBooster = False
        for role in member.roles:
            # TODO: Change "Server Booster" with API call to the premium guild role.
            if role.name == "Server Booster":
                isBooster = True
                break

    # Check for opt-out status
    if CHECK_OPT_OUT and member.id in opt_out_list:
        isOptedOut = True


    # Process color change
    if isBooster and not isCommand and not isCooldownActive and not isOptedOut:

        # Start the cooldown
        if USE_GLOBAL_COOLDOWN:
            globalCooldown = True
        else:
            cooldown.append(member.id)

        # Generate color (hex value stored in integer)
        color_r = int(random.random()*256)
        color_g = int(random.random()*256)
        color_b = int(random.random()*256)

        color = color_r*65536+color_g*256+color_b

        # Apply color change
        if CHECK_BOOSTER_ROLE:
            # TODO: Change "Server Booster" with API call to the premium guild role.
            role = discord.utils.get(server.roles, name="Server Booster")
            await role.edit(colour=discord.Colour(color))
        else:
            if not discord.utils.get(server.roles, name=member.name):
                await server.create_role(name=member.name, colour=discord.Colour(color))
                role = discord.utils.get(server.roles, name=member.name)
            else:
                role = discord.utils.get(server.roles, name=member.name)
                await role.edit(colour=discord.Colour(color))
            await member.add_roles(role)

        # Wait the cooldown duration
        await asyncio.sleep(COOLDOWN_TIME)

        if USE_GLOBAL_COOLDOWN:
            globalCooldown = False
        else:
            cooldown.remove(member.id)

    # I had this here for a good reason. I don't remember what that reason is.
    await bot.process_commands(message)

@bot.command()
async def opt_out(ctx):
    """
    Allows a user to opt out of the rolerave.

    :param ctx: ctx
    :return: None
    """
    global CHECK_OPT_OUT
    if CHECK_OPT_OUT:
        if not ctx.author.id in opt_out_list:
            opt_out_list.append(ctx.author.id)
            await ctx.send(f"Added {ctx.author.name} to the opt-out list!")
        else:
            opt_out_list.remove(ctx.author.id)
            await ctx.send(f"Removed {ctx.author.name} from the opt-out list!")

        opt_out_file = open("opt_out.json", "w")
        json.dump(opt_out_list, opt_out_file)
        opt_out_file.close()
    else:
        await ctx.send(f"The opt-out list is currently disabled!")

@bot.command()
async def opt_in(ctx):
    """
    Intended to alias opt_out.

    :param ctx: ctx
    :return: None
    """
    # TODO: There might be a better way to do this?
    await opt_out(ctx)

@bot.command()
@commands.has_permissions(administrator=True)
async def cooldown(ctx, arg):
    """
    Change the cooldown duration (in seconds)

    :param ctx: ctx
    :return: None
    """
    global COOLDOWN_TIME
    try:
        COOLDOWN_TIME = int(arg)
        await ctx.send(f"Set the cooldown time to {COOLDOWN_TIME} seconds!")
    except:
        await ctx.send(f"Unsuccessful. Cooldown time remains at {COOLDOWN_TIME} seconds!")

@bot.command()
@commands.has_permissions(administrator=True)
async def global_cooldown(ctx, arg):
    """
    Toggle global cooldowns

    :param ctx: ctx
    :return: None
    """
    global USE_GLOBAL_COOLDOWN
    if USE_GLOBAL_COOLDOWN:
        USE_GLOBAL_COOLDOWN = False
        await ctx.send(f"Turned off global cooldowns!")
    else:
        USE_GLOBAL_COOLDOWN = True
        await ctx.send(f"Turned on global cooldowns!")

@bot.command()
@commands.has_permissions(administrator=True)
async def require_booster(ctx, arg):
    """
    Toggle booster requirement

    :param ctx: ctx
    :return: None
    """
    global CHECK_BOOSTER_ROLE
    if CHECK_BOOSTER_ROLE:
        CHECK_BOOSTER_ROLE = False
        await ctx.send(f"Disabled the booster requirement!")
    else:
        CHECK_BOOSTER_ROLE = True
        await ctx.send(f"Enabled the booster requirement!")

@bot.command()
@commands.has_permissions(administrator=True)
async def enable_opt_out(ctx, arg):
    """
    Toggle opt-out ability

    :param ctx: ctx
    :return: None
    """
    global CHECK_OPT_OUT
    if CHECK_OPT_OUT:
        CHECK_OPT_OUT = False
        await ctx.send(f"Disabled the opt-out list!")
    else:
        CHECK_OPT_OUT = True
        await ctx.send(f"Enabled the opt-out list!")

@bot.command()
@commands.has_permissions(administrator=True)
async def enable_rave(ctx, arg):
    """
    Toggle opt-out ability

    :param ctx: ctx
    :return: None
    """
    global ENABLE_RAVE
    if ENABLE_RAVE:
        ENABLE_RAVE = False
        await ctx.send(f"Disabled the rave!")
    else:
        ENABLE_RAVE = True
        await ctx.send(f"Enabled the rave!")

# print(TOKEN)
bot.run(TOKEN)
