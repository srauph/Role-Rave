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

def load_file(filename):
    try:
        file = open(f"{filename}.json", "r")
        file_list = json.load(file)
        file.close()
    except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
        file = open(f"{filename}.json", "r")

        # Create it if it is missing
        if isinstance(e, FileNotFoundError):
            print(f"File {filename}.json not found, creating it...")

        # Recreate it if the file is bad
        elif isinstance(e, json.decoder.JSONDecodeError):
            print("WARNING: Json file corrupted, re-creating it...")
            file.close()
            create_old_file(filename)

        # Initialize the file
        file = open(f"{filename}.json", "w")
        json.dump([], file)
        file.close()
        file_list = []
    finally:
        return file_list

def process_boolean(arg, bool):
    """
    Assists in processing commands to set boolean values

    :param arg: On/true or off/false
    :param bool: The boolean value being adjusted
    :return: true/false according to arg, or bool if arg is invalid.
    """
    try:
        arg = arg.lower()
        if arg == "on" or arg == "true":
            return True
        elif arg == "off" or arg == "false":
            return False
        else:
            return bool
    except Exception:
        return bool

# Load the opt-out file
# try:
#     opt_out_file = open("opt_out.json", "r")
#     opt_out_list = json.load(opt_out_file)
#     opt_out_file.close()
# except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
#     opt_out_file = open("opt_out.json", "r")
#
#     # Create it if it is missing
#     if isinstance(e, FileNotFoundError):
#         print("File opt_out.json not found, creating it...")
#
#     # Recreate it if the file is bad
#     elif isinstance(e, json.decoder.JSONDecodeError):
#         print("WARNING: Json file corrupted, re-creating it...")
#         opt_out_file.close()
#         create_old_file("opt_out")
#
#     # Initialize the opt-out file
#     opt_out_file = open("opt_out.json", "w")
#     json.dump([], opt_out_file)
#     opt_out_file.close()
#     opt_out_list = []

# Load the opt-out file
opt_out_list = load_file("opt_out")

# client = discord.Client()
bot = commands.Bot(command_prefix='!', help_command=None)  # Bot object with command prefix

cooldown = []               # Per-User cooldown status
globalCooldown = False      # Global cooldown status
USE_GLOBAL_COOLDOWN = True  # Set to True to use the global cooldown
COOLDOWN_TIME = 3           # Cooldown time (seconds)
CHECK_BOOSTER_ROLE = True   # Require the users to be a booster for role rave
CHECK_OPT_OUT = True        # Check if the user opted out
ENABLE_RAVE = True          # Do the role rave shenanigans

# Load the constants file
constants_list = load_file("constants")
for i in constants_list:
    if i == "cooldown"

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
    if ENABLE_RAVE and isBooster and not isCommand and not isCooldownActive and not isOptedOut:

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
async def cooldown(ctx, arg=None):
    """
    Change the cooldown duration (in seconds)

    :param arg: Integer for cooldown duration (seconds)
    :param ctx: ctx
    :return: None
    """
    global COOLDOWN_TIME

    if arg == None:
        await ctx.send(f"The cooldown time is currently {COOLDOWN_TIME} seconds!")
    else:
        try:
            COOLDOWN_TIME = int(arg)
            await ctx.send(f"Set the cooldown time to {COOLDOWN_TIME} seconds!")
        except:
            await ctx.send(f"Unsuccessful. Cooldown time remains at {COOLDOWN_TIME} seconds!")

@bot.command()
@commands.has_permissions(administrator=True)
async def global_cooldown(ctx, arg=None):
    """
    Display global cooldowns status, and set it to on/true or off/false if a valid arg is passed.

    :param arg: On/True or off/false
    :param ctx: ctx
    :return: None
    """
    global USE_GLOBAL_COOLDOWN
    USE_GLOBAL_COOLDOWN = process_boolean(arg, USE_GLOBAL_COOLDOWN)
    await ctx.send(f"Global cooldowns status: {USE_GLOBAL_COOLDOWN}")

@bot.command()
@commands.has_permissions(administrator=True)
async def require_booster(ctx, arg=None):
    """
    Display booster requirement status, and set it to on/true or off/false if a valid arg is passed.

    :param arg: On/True or off/false
    :param ctx: ctx
    :return: None
    """
    global CHECK_BOOSTER_ROLE
    CHECK_BOOSTER_ROLE = process_boolean(arg, CHECK_BOOSTER_ROLE)
    await ctx.send(f"Booster requirement status: {CHECK_BOOSTER_ROLE}")

@bot.command()
@commands.has_permissions(administrator=True)
async def enable_opt_out(ctx, arg=None):
    """
    Display opt-out ability status, and set it to on/true or off/false if a valid arg is passed.

    :param arg: On/True or off/false
    :param ctx: ctx
    :return: None
    """
    global CHECK_OPT_OUT
    CHECK_OPT_OUT = process_boolean(arg, CHECK_OPT_OUT)
    await ctx.send(f"Opt-out list status: {CHECK_OPT_OUT}")

@bot.command()
@commands.has_permissions(administrator=True)
async def enable_rave(ctx, arg=None):
    """
    Display rave status, and set it to on/true or off/false if a valid arg is passed.

    :param arg: On/True or off/false
    :param ctx: ctx
    :return: None
    """
    global ENABLE_RAVE
    ENABLE_RAVE = process_boolean(arg, ENABLE_RAVE)
    await ctx.send(f"Rave status: {ENABLE_RAVE}")

@bot.command()
async def help(ctx):
    """
    Displays commands list.

    :param ctx: ctx
    :return: None
    """
    isAdmin = ctx.author.guild_permissions.administrator
    isBooster = False
    for r in ctx.author.roles:
        if "Server Booster" in r.name:
            isBooster = True
            break


    embed = discord.Embed(
        colour = discord.Colour.magenta()
    )

    embed.set_author(name="Commands list!")

    if isBooster or isAdmin:
        embed.add_field(
            name="!opt_out",
            value="Opts out of the rolerave (Alias: !opt_in)",
            inline=False
        )

    if isAdmin:
        embed.add_field(
            name="!cooldown",
            value="Displays the cooldown duration, and change it to [duration] seconds if a valid duration is passed.",
            inline=False
        )
        embed.add_field(
            name="!cooldown [duration]",
            value="Change the cooldown duration ",
            inline=False
        )
        embed.add_field(
            name="!global_cooldown [on/true or off/false]",
            value="Display the global cooldown status; set it to on (true) or off (false) if a valid arg is passed.",
            inline=False
        )
        embed.add_field(
            name="!require_booster [on/true or off/false]",
            value="Display the booster requirement status; set it to on (true) or off (false) if a valid arg is passed.",
            inline=False
        )
        embed.add_field(
            name="!enable_opt_out [on/true or off/false]",
            value="Display the opt-out ability status; set it to on (true) or off (false) if a valid arg is passed.",
            inline=False
        )
        embed.add_field(
            name="!enable_rave [on/true or off/false]",
            value="Display the rave status; set it to on (true) or off (false) if a valid arg is passed.",
            inline=False
        )

    embed.add_field(name="!help", value="Displays this help message", inline=False)

    await ctx.send(embed=embed)

# print(TOKEN)
bot.run(TOKEN)
