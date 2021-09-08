import os
import discord
import random
import asyncio
import json
import traceback
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
    newname = filename + "_old.json"
    num = 1
    while os.path.exists(newname):
        newname = filename + "_old" + str(num) + ".json"
        num += 1
    os.rename(filename + ".json", newname)


def load_file(filename):
    """
    Handles loading a json file, including cases where the file doesn't exist or is corrupted.

    :param filename: Name of the file without extension
    :return: A list generated from the json data in the file.
    """
    file_list = []
    try:
        print(f"Opening {filename}.json... ", end='')
        file = open(f"{filename}.json", "r")
        file_list = json.load(file)
        file.close()
    except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
        print("error:")

        # Create it if it is missing
        if isinstance(e, FileNotFoundError):
            print(f"File {filename}.json not found, creating it... ", end='')

        # Recreate it if the file is bad
        elif isinstance(e, json.decoder.JSONDecodeError):
            print(f"WARNING: {filename}.json file corrupted, re-creating it... ", end='')
            file.close()
            create_old_file(filename)

        # Initialize the file
        file = open(f"{filename}.json", "w")
        json.dump([], file)
        file.close()
        file_list = []
    finally:
        print("done.")
        return file_list


def process_boolean(arg, boolean):
    """
    Assists in processing commands to set boolean values

    :param arg: On/true or off/false
    :param boolean: The boolean value being adjusted
    :return: true/false according to arg, or bool if arg is invalid.
    """
    try:
        arg = arg.lower()
        if arg == "on" or arg == "true":
            return True
        elif arg == "off" or arg == "false":
            return False
        else:
            return boolean
    except Exception:
        return boolean



# Bot object with command prefix
bot = commands.Bot(
    command_prefix='!',
    help_command=None
)

# Servers list
servers = {}

def check_server(server):
    global servers
    if server in servers:
        rave = servers[server]
    else:
        rave = Rave(server)
        servers[server] = rave
    return rave

class Rave:
    def __init__(self, server):
        self.cooldown = []  # Per-User cooldown status
        self.globalCooldown = False  # Global cooldown status
        self.server = str(server)

        self.useGlobalCooldown = True  # Set to True to use the global cooldown
        self.cooldownTime = 30  # Cooldown time (seconds)
        self.checkRole = True  # Require the users to have the required role for role rave
        self.requiredRole = "Server Booster"  # Required role for the role rave
        self.useRequiredRole = False  # Whether or not to use the required role for the role rave
        self.checkOptOut = True  # Check if the user opted out
        self.enableRave = True  # Do the role rave shenanigans
        self.moveRole = False  # Whether or not to move rave roles
        self.moveRoleAmt = 2  # How much to move roles from top (negative values: from bottom)

        # Variables for regulating blacklisted color ranges
        self.blacklist = []  # [(r, g, b), tolerance] list of blacklisted colors and matching tolerances BB: [(46, 204, 113), 0.2], [(52, 152, 219), 0.2]
        self.blacklist_range = []  # 2-tuples of (r, g, b) tuples of blacklisted colors, each indicating a blacklisted range
        self.defaultTolerance = 0.2  # Default amount which a color is allowed to differ from a blacklisted one

        # Load files
        self.opt_out_list = load_file("opt_out_"+self.server)
        self.variables_list = load_file("variables_"+self.server)

        # Load saved vairables unless variables_list is empty
        if self.variables_list == []:
            self.save_variables()
        else:
            self.load_variables()

        # Create blacklisted ranges
        self.generate_blacklist_range()

    def save_variables(self):
        """
        Save the variables to variables.json

        :return: None
        """
        # global self.variables_list
        self.variables_list = [
            ("useGlobalCooldown", self.useGlobalCooldown),
            ("cooldownTime", self.cooldownTime),
            ("checkRole", self.checkRole),
            ("requiredRole", self.requiredRole),
            ("useRequiredRole", self.useRequiredRole),
            ("checkOptOut", self.checkOptOut),
            ("enableRave", self.enableRave),
            ("blacklist", self.blacklist),
            ("blacklist_range", self.blacklist_range),
            ("defaultTolerance", self.defaultTolerance),
            ("moveRole", self.moveRole),
            ("moveRoleAmt", self.moveRoleAmt)
        ]

        variables_file = open(f"variables_{self.server}.json", "w")
        json.dump(self.variables_list, variables_file)
        variables_file.close()

    def load_variables(self):
        """
        Load the variables from variables_list

        :return: None
        """
        # global variables_list
        # global useGlobalCooldown, cooldownTime, checkRole, checkOptOut, enableRave
        for v in self.variables_list:
            if v[0] == "useGlobalCooldown": self.useGlobalCooldown = v[1]
            if v[0] == "cooldownTime": self.cooldownTime = v[1]
            if v[0] == "checkRole": self.checkRole = v[1]
            if v[0] == "requiredRole": self.requiredRole = v[1]
            if v[0] == "useRequiredRole": self.useRequiredRole = v[1]
            if v[0] == "checkOptOut": self.checkOptOut = v[1]
            if v[0] == "enableRave": self.enableRave = v[1]
            if v[0] == "blacklist": self.blacklist = v[1]
            if v[0] == "blacklist_range": self.blacklist_range = v[1]
            if v[0] == "defaultTolerance": self.defaultTolerance = v[1]
            if v[0] == "moveRole": self.moveRole = v[1]
            if v[0] == "moveRoleAmt": self.moveRoleAmt = v[1]

    def generate_blacklist_range(self):
        for i in self.blacklist:
            color = i[0]
            tolerance = i[1]
            r_min = int(color[0] * (1 - tolerance)) if 0 <= int(color[0] * (1 - tolerance)) else 0
            g_min = int(color[1] * (1 - tolerance)) if 0 <= int(color[1] * (1 - tolerance)) else 0
            b_min = int(color[2] * (1 - tolerance)) if 0 <= int(color[2] * (1 - tolerance)) else 0
            r_max = int(color[0] * (1 + tolerance)) if int(color[0] * (1 + tolerance)) <= 255 else 255
            g_max = int(color[1] * (1 + tolerance)) if int(color[1] * (1 + tolerance)) <= 255 else 255
            b_max = int(color[2] * (1 + tolerance)) if int(color[2] * (1 + tolerance)) <= 255 else 255
            self.blacklist_range.append(((r_min, g_min, b_min), (r_max, g_max, b_max)))





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

    global servers
    # global cooldown
    # global globalCooldown
    # global enableRave

    member = message.author
    server = message.guild
    serverStr = str(message.guild.id)+"."+str(message.guild)
    rave = check_server(serverStr)

    isCommand = False  # Set to true if message is a command
    isCooldownActive = False  # Set to true if the cooldown is active
    isOptedOut = False  # Set to true if user opted out (if applicable)
    isRequiredRole = True  # Set to false if CHECK_BOOSTER_ROLE and if member is not a booster

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
    if rave.useGlobalCooldown:
        isCooldownActive = rave.globalCooldown
    else:
        if member.id in rave.cooldown:
            isCooldownActive = True

    # Check for required role
    if rave.checkRole:
        isRequiredRole = False
        for role in member.roles:
            if role.name == rave.requiredRole:
                isRequiredRole = True
                break

    # Check for opt-out status
    if rave.checkOptOut and member.id in rave.opt_out_list:
        isOptedOut = True

    # Process color change
    if rave.enableRave and isRequiredRole and not isCommand and not isCooldownActive and not isOptedOut:

        # Start the cooldown
        if rave.useGlobalCooldown:
            rave.globalCooldown = True
        else:
            rave.cooldown.append(member.id)

        # Generate color (hex value stored in integer)
        unacceptable_color = True
        while unacceptable_color:

            color_r = int(random.random() * 256)
            color_g = int(random.random() * 256)
            color_b = int(random.random() * 256)

            unacceptable_color = False

            for clr in rave.blacklist_range:
                if clr[0][0] <= color_r <= clr[1][0] \
                        and clr[0][1] <= color_g <= clr[1][1] \
                        and clr[0][2] <= color_b <= clr[1][2]:
                    unacceptable_color = True
                    break

        color = color_r * 65536 + color_g * 256 + color_b

        # Apply color change
        if rave.useRequiredRole:
            role = discord.utils.get(server.roles, name=rave.requiredRole)
            await role.edit(colour=discord.Colour(color))
        else:
            rolesNum = len(server.roles)
            if not discord.utils.get(server.roles, name=str(member)):
                await server.create_role(name=str(member), colour=discord.Colour(color))
                role = discord.utils.get(server.roles, name=str(member))
                if rave.moveRole:
                    if rave.moveRoleAmt > 0:
                        await server.edit_role_positions(positions={role: rolesNum-rave.moveRoleAmt})
                    else:
                        await server.edit_role_positions(positions={role: -rave.moveRoleAmt})
            else:
                role = discord.utils.get(server.roles, name=str(member))
                await role.edit(colour=discord.Colour(color))
            await member.add_roles(role)

        # Wait the cooldown duration
        await asyncio.sleep(rave.cooldownTime)

        if rave.useGlobalCooldown:
            rave.globalCooldown = False
        else:
            rave.cooldown.remove(member.id)

    # I had this here for a good reason. I don't remember what that reason is.
    await bot.process_commands(message)


@bot.command()
async def opt_out(ctx):
    """
    Allows a user to opt out of the rolerave.

    :param ctx: ctx
    :return: None
    """
    # global checkOptOut
    server = str(ctx.guild.id)+"."+str(ctx.guild)
    rave = check_server(server)

    if rave.checkOptOut:
        if ctx.author.id not in rave.opt_out_list:
            rave.opt_out_list.append(ctx.author.id)
            await ctx.send(f"Added {ctx.author.name} to the opt-out list!")
        else:
            await ctx.send(f"{ctx.author.name}, you already opted out!")

        opt_out_file = open(f"opt_out_{server}.json", "w")
        json.dump(rave.opt_out_list, opt_out_file)
        opt_out_file.close()
    else:
        await ctx.send(f"The opt-out list is currently disabled!")


@bot.command()
async def opt_in(ctx):
    """
    Allows a user to opt back into the rolerave.

    :param ctx: ctx
    :return: None
    """
    # global checkOptOut
    server = str(ctx.guild.id)+"."+str(ctx.guild)
    rave = check_server(server)

    if rave.checkOptOut:
        if ctx.author.id in rave.opt_out_list:
            rave.opt_out_list.remove(ctx.author.id)
            await ctx.send(f"Removed {ctx.author.name} from the opt-out list!")
        else:
            await ctx.send(f"{ctx.author.name}, you're already opted in!")

        opt_out_file = open(f"opt_out_{server}.json", "w")
        json.dump(rave.opt_out_list, opt_out_file)
        opt_out_file.close()
    else:
        await ctx.send(f"The opt-out list is currently disabled!")

@bot.command()
async def color(ctx, *args):
    """
    Allows a user to see what another user's role's color is.

    :param ctx: ctx
    :param arg: User's name
    :return: None
    """
    arg = "".join(args[:])
    server = ctx.guild
    serverStr = str(ctx.guild.id) + "." + str(ctx.guild)
    rave = check_server(serverStr)

    if rave.useRequiredRole:
        role = discord.utils.get(server.roles, name=rave.requiredRole)
    else:
        if arg != '':
            if len(arg) < 5 or not arg[-5] == '#':
                roles = server.roles
                for i in roles:
                    if i.name.split('#')[0].lower() == arg:
                        role = i
            else:
                role = discord.utils.get(server.roles, name=arg)
        else:
            role = discord.utils.get(server.roles, name=str(ctx.author))
    try:
        await ctx.send(f"The color is {role.colour}.")
    except:
        await ctx.send(f"The role or user could not be found.")


@bot.command()
@commands.has_permissions(administrator=True)
async def cooldown(ctx, arg=None):
    """
    Change the cooldown duration (in seconds)

    :param arg: Integer for cooldown duration (seconds)
    :param ctx: ctx
    :return: None
    """
    # global cooldownTime
    server = str(ctx.guild.id)+"."+str(ctx.guild)
    rave = check_server(server)

    if arg is None:
        await ctx.send(f"The cooldown time is currently {rave.cooldownTime} seconds!")
    else:
        try:
            rave.cooldownTime = int(arg)
            await ctx.send(f"Set the cooldown time to {rave.cooldownTime} seconds!")
            rave.save_variables()
        except ValueError:
            await ctx.send(f"Value must be a number. Cooldown time remains at {rave.cooldownTime} seconds!")
        except:
            await ctx.send(f"Unsuccessful. Cooldown time remains at {rave.cooldownTime} seconds!")


@bot.command()
@commands.has_permissions(administrator=True)
async def global_cooldown(ctx, arg=None):
    """
    Display global cooldowns status, and set it to on/true or off/false if a valid arg is passed.

    :param arg: On/True or off/false
    :param ctx: ctx
    :return: None
    """
    # global useGlobalCooldown
    server = str(ctx.guild.id)+"."+str(ctx.guild)
    rave = check_server(server)

    rave.useGlobalCooldown = process_boolean(arg, rave.useGlobalCooldown)
    if arg is not None:
        rave.save_variables()
    await ctx.send(f"Global cooldowns status: {rave.useGlobalCooldown}")


@bot.command()
@commands.has_permissions(administrator=True)
async def require_role(ctx, arg=None):
    """
    Display role requirement status, and set it to on/true or off/false if a valid arg is passed.

    :param arg: On/True or off/false
    :param ctx: ctx
    :return: None
    """
    # global checkRole
    server = str(ctx.guild.id)+"."+str(ctx.guild)
    rave = check_server(server)

    rave.checkRole = process_boolean(arg, rave.checkRole)
    if arg is not None:
        rave.save_variables()
    await ctx.send(f"Role requirement status: {rave.checkRole}")


@bot.command()
@commands.has_permissions(administrator=True)
async def required_role(ctx, arg=None):
    """
    View or change the required role.

    :param ctx: ctx
    :param arg: The role to change to
    :return: None
    """
    server = ctx.guild
    serverStr = str(ctx.guild.id) + "." + str(ctx.guild)
    rave = check_server(serverStr)

    role = discord.utils.get(server.roles, name=arg)
    if arg is not None:
        if role is not None:
            rave.requiredRole = str(role)
            rave.save_variables()
        else:
            await ctx.send(f"Role not found. Required role: {rave.requiredRole}")
    else:
        await ctx.send(f"Required role: {rave.requiredRole}")


@bot.command()
@commands.has_permissions(administrator=True)
async def use_required_role(ctx, arg=None):
    """
    View and set whether or not to change the required role's color (instead of users' colors).

    :param arg: On/True or off/false
    :param ctx: ctx
    :return: None
    """
    # global checkOptOut
    server = str(ctx.guild.id)+"."+str(ctx.guild)
    rave = check_server(server)

    rave.useRequiredRole = process_boolean(arg, rave.useRequiredRole)
    if arg is not None:
        rave.save_variables()
    await ctx.send(f"Use required role status: {rave.useRequiredRole}")


@bot.command()
@commands.has_permissions(administrator=True)
async def move_role(ctx, arg1=None, arg2=None):
    """
    Whether or not to move rolerave roles.

    :param arg1: On/True or off/false
    :param arg2: Amount to move role by
    :param ctx: ctx
    :return: None
    """
    # global useGlobalCooldown
    server = str(ctx.guild.id)+"."+str(ctx.guild)
    rave = check_server(server)

    rave.moveRole = process_boolean(arg1, rave.moveRole)
    if arg1 is not None:
        if arg2 is not None:
            try:
                rave.moveRoleAmt = int(arg2)
            except:
                await ctx.send(f"Could not adjust role adjustment amount.")
        rave.save_variables()
    await ctx.send(f"Move role status: {rave.moveRole}; amount: {rave.moveRoleAmt}")


@bot.command()
@commands.has_permissions(administrator=True)
async def enable_opt_out(ctx, arg=None):
    """
    Display opt-out ability status, and set it to on/true or off/false if a valid arg is passed.

    :param arg: On/True or off/false
    :param ctx: ctx
    :return: None
    """
    # global checkOptOut
    server = str(ctx.guild.id)+"."+str(ctx.guild)
    rave = check_server(server)

    rave.checkOptOut = process_boolean(arg, rave.checkOptOut)
    if arg is not None:
        rave.save_variables()
    await ctx.send(f"Opt-out list status: {rave.checkOptOut}")


@bot.command()
@commands.has_permissions(administrator=True)
async def enable_rave(ctx, arg=None):
    """
    Display rave status, and set it to on/true or off/false if a valid arg is passed.

    :param arg: On/True or off/false
    :param ctx: ctx
    :return: None
    """
    # global enableRave
    server = str(ctx.guild.id)+"."+str(ctx.guild)
    rave = check_server(server)

    rave.enableRave = process_boolean(arg, rave.enableRave)
    if arg is not None:
        rave.save_variables()
    await ctx.send(f"Rave status: {rave.enableRave}")


@bot.command()
@commands.has_permissions(administrator=True)
async def blacklist(ctx, operation=None, arg1=None, arg2=None):
    """
    Display currently blacklisted colours, and add/remove a role/color if a valid arg is passed.
    :param ctx:
    :param arg:
    :return:
    """

    server = ctx.guild
    serverStr = str(ctx.guild.id)+"."+str(ctx.guild)
    rave = check_server(serverStr)

    if operation is not None:
        try:
            operation = operation.lower()
            if operation != "add" and operation != "remove":
                await ctx.send("Operation must be either `add` or `remove`.")
                raise Exception

            if arg2 is None:
                tolerance = rave.defaultTolerance
            else:
                try:
                    tolerance = float(arg2)
                    if not 0.01 <= tolerance <= 0.99:
                        raise ValueError
                except ValueError:
                    await ctx.send("Tolerance must be a number, and it must be between 0.01 and 0.99.")
                    raise Exception

            role = discord.utils.get(server.roles, name=arg1)
            if role is not None:
                colors = [(role.colour.r, role.colour.g, role.colour.b), tolerance]
            else:
                try:
                    # TODO: replace this with regex
                    colors = arg1.replace('(', '').replace(')', '').replace(' ', '')
                    colors = colors.split(',', 2)
                    colors = [(int(colors[0]), int(colors[1]), int(colors[2])), tolerance]
                except:
                    await ctx.send("Invalid color or role.")
                    raise Exception

            if operation == "add":
                for r in rave.blacklist:
                    if r[0] == colors[0]:
                        await ctx.send("Color already exists in blacklist set... If you wish to update the tolerance, remove it first, then re-add it.")
                        raise Exception
                rave.blacklist.append(colors)
                rave.generate_blacklist_range()

            elif operation == "remove":
                removed = False
                for r in rave.blacklist:
                    if r[0] == colors[0]:
                        rave.blacklist.remove(r)
                        removed = True
                if not removed:
                    await ctx.send("Could not find color to remove.")
                    raise Exception

            rave.save_variables()
            await ctx.send(f"Blacklisted colours (R,G,B,Tolerance): {rave.blacklist}")

        except Exception:
            # traceback.print_exc()
            await ctx.send("Usage: `!blacklist [<operation> <R,G,B OR role name> [Tolerance]]`")

    else:
        await ctx.send(f"Blacklisted colours (R,G,B,Tolerance): {rave.blacklist}")

@bot.command()
@commands.has_permissions(administrator=True)
async def default_blacklist_tolerance(ctx, arg=None):
    """
    Change the default blacklist tolerance

    :param arg: Float for default blacklist tolerance (between 0.01 and 0.99)
    :param ctx: ctx
    :return: None
    """
    # global cooldownTime
    server = str(ctx.guild.id)+"."+str(ctx.guild)
    rave = check_server(server)

    if arg is None:
        await ctx.send(f"The default blacklist tolerance is currently {rave.defaultTolerance}.")
    else:
        try:
            tolerance = float(arg)
            if not 0.01 <= tolerance <= 0.99:
                raise ValueError

            rave.defaultTolerance = tolerance
            await ctx.send(f"Set the default blacklist tolerance to {rave.defaultTolerance}!")
            rave.save_variables()
        except ValueError:
            await ctx.send(f"Value must be between 0.01 and 0.99. Default blacklist tolerance time remains at {rave.defaultTolerance}.")
        except:
            await ctx.send(f"Unsuccessful. Default blacklist tolerance time remains at {rave.defaultTolerance}.")

@bot.command()
async def help(ctx):
    """
    Displays commands list.

    :param ctx: ctx
    :return: None
    """
    server = str(ctx.guild.id)+"."+str(ctx.guild)
    rave = check_server(server)

    isAdmin = ctx.author.guild_permissions.administrator
    isRequiredRole = not rave.checkRole

    for r in ctx.author.roles:
        if rave.requiredRole in r.name:
            isRequiredRole = True
            break

    embed = discord.Embed(
        colour=discord.Colour.magenta()
    )

    embed.set_author(name="Commands list!")

    if isRequiredRole or isAdmin:
        embed.add_field(
            name="!opt_out",
            value="Opts out of the rolerave.",
            inline=False
        )
        embed.add_field(
            name="!opt_in",
            value="Opts in to the rolerave.",
            inline=False
        )
        embed.add_field(
            name="!color [name or DiscordID]",
            value="Displays the color of your name, of the specified name, or of the DiscordID (Discord IDs are case-sensitive!)",
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
            value="Change the cooldown duration.",
            inline=False
        )
        embed.add_field(
            name="!global_cooldown [on/true or off/false]",
            value="Display the global cooldown status; set it to on (true) or off (false) if a valid arg is passed.",
            inline=False
        )
        embed.add_field(
            name="!require_role [on/true or off/false]",
            value="Display the role requirement status; set it to on (true) or off (false) if a valid arg is passed.",
            inline=False
        )
        embed.add_field(
            name="!required_role [role]",
            value="Change the required role.",
            inline=False
        )
        embed.add_field(
            name="!move_role [on/true or off/false] [amount]",
            value="Whether or not to move the rolerave roles, and by how much (if on).",
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
        embed.add_field(
            name="!blacklist [<operation> <R,G,B OR role name> [Tolerance]]",
            value="Display the blacklist... \n\
            <operation>: `add` if you are adding an element to the blacklist, or `remove` if you are removing an element to it, \n\
            <R,G,B OR role name>: The `R,G,B` value of the color to add/remove. Specifying a role name will copy the role's CURRENT color (will need to be updated if the role color changes), \n\
            [Tolerance]: The tolerance for a given role color. Must be between 0.01 and 0.99.",
            inline=False
        )
        embed.add_field(
            name="!default_blacklist_tolerance [tolerance]",
            value="Change the default blacklist tolerance.",
            inline=False
        )

    embed.add_field(name="!help", value="Displays this help message", inline=False)

    await ctx.send(embed=embed)


# print(TOKEN)
bot.run(TOKEN)
