import asyncio
import json
import os
import sys
import traceback

import aiohttp
import asqlite
import discord
from discord.ext import tasks, commands


# Initialize bot
intents = discord.Intents.none()
intents.guilds = intents.members = intents.integrations = intents.guilds = intents.messages = True
bot = commands.Bot(
    command_prefix="<@1012707426107134002> ",
    help_command=commands.MinimalHelpCommand(),
    case_insensitive=True,
    intents=intents
)


@bot.hybrid_command()
@commands.guild_only()
@commands.has_guild_permissions(administrator=True)
async def ping(ctx):
    """
    Sends bot latency
    Usage: ping

    :param ctx: Context object
    """
    if ctx.interaction is not None:
        await ctx.reply(f'Pong! {int(bot.latency * 1000)}ms', ephemeral=True)
    else:
        await ctx.send(f'Pong! {int(bot.latency * 1000)}ms')


@bot.hybrid_command(name='role')
@commands.guild_only()
@commands.has_guild_permissions(administrator=True)
async def set_verification_role(ctx, role: discord.Role):
    """
    Sets the WPI Verification role to give to users
    Usage: verifyRole

    :param ctx: Context object
    :param role: Role
    """
    async with bot.conn.cursor() as cursor:
        verified_role = (
            await (
                await cursor.execute("SELECT verification_role FROM guilds WHERE id = ?", ctx.guild.id)
            ).fetchone()
        )[0]

        if verified_role is not None:
            if role.id is verified_role:
                response = "This is already the verified role"
            else:
                await cursor.execute("UPDATE guilds SET verification_role = ?", role.id)
                await bot.conn.commit()
                response = f"Updated verification role to <@&{role.id}>"

        else:
            await cursor.execute("UPDATE guilds SET verification_role = ?", role.id)
            await bot.conn.commit()
            response = f"Updated verification role to <@&{role.id}>"

    if ctx.interaction is not None:
        await ctx.reply(response, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
    else:
        await ctx.send_message(response, allowed_mentions=discord.AllowedMentions.none())

    await update_users(ctx)


@bot.hybrid_command(name='disable')
@commands.guild_only()
@commands.has_guild_permissions(administrator=True)
async def remove_verification_role(ctx):
    """
    Disables verification updates.

    :param ctx: Context object
    """
    async with bot.conn.cursor() as cursor:
        verified_role = (
            await (
                await cursor.execute("SELECT verification_role FROM guilds WHERE id = ?", ctx.guild.id)
            ).fetchone()
        )[0]
        verified_role = ctx.guild.get_role(verified_role)

        if verified_role is not None:
            await cursor.execute("UPDATE guilds SET verification_role = ?", None)
            await bot.conn.commit()
            response = 'Disabled verifications.'
        else:
            response = 'Verification is already disabled'

    if ctx.interaction is not None:
        await ctx.reply(response, ephemeral=True)
    else:
        await ctx.send_message(response)


@bot.hybrid_command(name='require')
@commands.guild_only()
@commands.has_guild_permissions(administrator=True)
async def add_required_roles(ctx, role: discord.Role):
    """
    Sets a required role to pick up the WPI Verification role

    :param ctx: Context object
    :param role: Role to require
    """
    async with bot.conn.cursor() as cursor:
        required_roles = (
            await (
                await cursor.execute("SELECT required_roles FROM guilds WHERE id = ?", ctx.guild.id)
            ).fetchone()
        )[0]

        if required_roles is not None:
            r_role = json.loads(required_roles)
            if role.id not in r_role:
                r_role.append(role.id)
                await cursor.execute("UPDATE guilds SET required_roles = ?", json.dumps(r_role))
                await bot.conn.commit()
                response = f"Added <@&{role.id}> to the list of required roles"
            else:
                response = f"<@&{role.id}> is already a required role"
        else:
            await cursor.execute("UPDATE guilds SET required_roles = ?", json.dumps([role.id]))
            await bot.conn.commit()
            response = f"Added <@&{role.id}> to the list of required roles"

    if ctx.interaction is not None:
        await ctx.reply(response, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
    else:
        await ctx.send_message(response, allowed_mentions=discord.AllowedMentions.none())

    await update_users(ctx)


@bot.hybrid_command(name='remove')
@commands.guild_only()
@commands.has_guild_permissions(administrator=True)
async def remove_required_roles(ctx, role: discord.Role):
    """
    Removes a required role to gain the WPI Verification role

    :param ctx: Context object
    :param role: Role to remove
    """
    async with bot.conn.cursor() as cursor:
        required_roles = (
            await (
                await cursor.execute("SELECT required_roles FROM guilds WHERE id = ?", ctx.guild.id)
            ).fetchone()
        )[0]

        if required_roles is not None:
            required_roles = json.loads(required_roles)
            if role.id in required_roles:
                required_roles.remove(role.id)
                await cursor.execute("UPDATE guilds SET required_roles = ?", json.dumps(required_roles))
                await bot.conn.commit()
                response = f"Removed <@&{role.id}> from the list of required roles"
            else:
                response = f"Couldn't find <@&{role.id}> in the list of required roles"
        else:
            response = f"You don't have any required roles"

    if ctx.interaction is not None:
        await ctx.reply(response, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
    else:
        await ctx.send_message(response, allowed_mentions=discord.AllowedMentions.none())

    await update_users(ctx)


@bot.hybrid_command(name='config')
@commands.guild_only()
@commands.has_guild_permissions(administrator=True)
async def config(ctx):
    """
    Shows the config for the current server

    :param ctx: Context object
    """
    async with bot.conn.cursor() as cursor:
        verification_role = (
            await (
                await cursor.execute("SELECT verification_role FROM guilds WHERE id = ?", ctx.guild.id)
            ).fetchone()
        )[0]
        if verification_role is None:
            verification_role = None
        else:
            verification_role = f"<@&{verification_role}>"

        required_role = (
            await (
                await cursor.execute("SELECT required_roles FROM guilds WHERE id = ?", ctx.guild.id)
            ).fetchone()
        )[0]

        if required_role != "[]" and required_role is not None:
            required_role = json.loads(required_role)
            required_role = f"<@&{'>, '.join([str(x) for x in required_role])}>"
        else:
            required_role = None

        if ctx.interaction is not None:
            await ctx.reply(
                f"Verification Role: {verification_role}\nRequired Roles: {required_role}",
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none()
            )
        else:
            await ctx.send_message(
                f"Verification Role: {verification_role}\nRequired Roles: {required_role}",
                allowed_mentions=discord.AllowedMentions.none()
            )


@bot.tree.command()
@commands.guild_only()
async def verify(interaction):
    """
    Sends verification information

    :param interaction: Interaction object
    """
    async with bot.conn.cursor() as cursor:
        user = await (
            await cursor.execute("SELECT discord_id FROM users WHERE discord_id = ?", interaction.user.id)
        ).fetchone()

        if user is None:
            await interaction.response.send_message(f'You can verify at https://www.gompeibot.com', ephemeral=True)
        else:
            verified_role = (
                await (
                    await cursor.execute("SELECT verification_role FROM guilds WHERE id = ?", interaction.guild.id)
                ).fetchone()
            )[0]

            verified_role = interaction.guild.get_role(verified_role)
            if verified_role is None:
                await interaction.response.send_message(
                    "You've already verified but this guild doesn't have a verification role", ephemeral=True
                )
            elif verified_role in interaction.user.roles:
                await interaction.response.send_message("You're already verified!", ephemeral=True)
            else:
                required_roles = (
                    await (
                        await cursor.execute("SELECT required_roles FROM guilds WHERE id = ?", interaction.guild.id)
                    ).fetchone()
                )[0]

                if required_roles != "[]" and required_roles is not None:
                    required_roles = json.loads(required_roles)
                    required_roles = f"<@&{'>, '.join([str(x) for x in required_roles])}>"
                else:
                    required_roles = None

                await interaction.response.send_message(
                    f"You're verified, but need to have one of these roles to verify: {required_roles}",
                    ephemeral=True,
                    allowed_mentions=discord.AllowedMentions.none()
                )


async def update_users(ctx):
    """
    Updates verified users in a server based on requirements

    :param ctx: Context object
    """
    async with bot.conn.cursor() as cursor:
        verified_role = (
            await (
                await cursor.execute("SELECT verification_role FROM guilds WHERE id = ?", ctx.guild.id)
            ).fetchone()
        )[0]
        required_roles = (
            await (
                await cursor.execute("SELECT required_roles FROM guilds WHERE id = ?", ctx.guild.id)
            ).fetchone()
        )[0]

        verified_role = ctx.guild.get_role(verified_role)
        if verified_role is None:
            return

        if required_roles is None or required_roles == '[]':
            required_roles = []
        else:
            required_roles = json.loads(required_roles)
            required_roles = [ctx.guild.get_role(x) for x in required_roles if x is not None]

        for member in ctx.guild.members:
            user = await (
                await cursor.execute("SELECT discord_id FROM users WHERE discord_id = ?", member.id)
            ).fetchone()

            if user is None:
                continue

            if verified_role in member.roles:
                if len(required_roles) > 0:
                    for role in required_roles:
                        if role in member.roles:
                            break
                    else:
                        await member.remove_roles(verified_role, reason='Missing role requirements')
                        continue

            if len(required_roles) > 0:
                for role in required_roles:
                    if role in required_roles:
                        break
                else:
                    break

            await member.add_roles(verified_role, reason='Passed role requirements on check')


@tasks.loop(seconds=5.0)
async def update_wpi_verifications():
    """
    Checks the verification list and returns new WPI verified IDs

    :return: List of new IDs
    """

    # /var/www/WPI-Discord-Flask/
    # Open the verification file and read the user IDs. Compare to the ones stored here.
    with open("verifications.json", "r+") as file:
        verifications = json.loads(file.read())

    async with bot.conn.cursor() as cursor:
        for token in verifications:
            user = await (await cursor.execute("SELECT home_id FROM users WHERE home_id = ?", token)).fetchone()
            if user is None:
                await cursor.execute("INSERT INTO users VALUES (?, ?)", (token, verifications[token]))

    await bot.conn.commit()


@bot.command()
@commands.is_owner()
async def terminate(ctx):
    """Cleanly exits the bot process"""
    await ctx.send(f'Terminating the bot')
    await bot.session.close()
    await bot.conn.close()
    await bot.close()


@bot.command()
@commands.is_owner()
async def sync(ctx):
    """
    Syncs application commands globally

    :param ctx: Context object
    """
    synced = await ctx.bot.tree.sync()
    await ctx.send(f"Synced {len(synced)} commands")


# Load default events
@bot.event
async def on_ready():
    """Loads default settings"""
    await guild_check()
    print("Logged on as {0}".format(bot.user))


@bot.event
async def on_member_join(member):
    """Checks verification status of member on join"""
    async with bot.conn.cursor() as cursor:
        user = await (await cursor.execute("SELECT discord_id FROM users WHERE discord_id = ?", member.id)).fetchone()
        if user is None:
            return

        verification_role = (
            await (
                await cursor.execute("SELECT verification_role FROM guilds WHERE id = ?", member.guild.id)
            ).fetchone()
        )[0]
        verification_role = member.guild.get_role(verification_role)
        if verification_role is None:
            return

        required_roles = (
            await (
                await cursor.execute("SELECT required_roles FROM guilds WHERE id = ?", member.guild.id)
            ).fetchone()
        )[0]
        if required_roles is not None and required_roles != '[]':
            return

        await member.add_roles(verification_role, reason='Verified on join')


@bot.event
async def on_member_update(before, after):
    """Checks if the member picked up a required role"""
    async with bot.conn.cursor() as cursor:
        user = await (await cursor.execute("SELECT discord_id FROM users WHERE discord_id = ?", before.id)).fetchone()
        if user is None:
            return

        verification_role = (
            await (
                await cursor.execute("SELECT verification_role FROM guilds WHERE id = ?", before.guild.id)
            ).fetchone()
        )[0]
        verification_role = before.guild.get_role(verification_role)
        if verification_role is None:
            return

        required_roles = (
            await (
                await cursor.execute("SELECT required_roles FROM guilds WHERE id = ?", before.guild.id)
            ).fetchone()
        )[0]

        if required_roles is None or required_roles == '[]':
            required_roles = []
        else:
            required_roles = json.loads(required_roles)
            required_roles = [before.guild.get_role(x) for x in required_roles if x is not None]

        if verification_role in after.roles:
            if len(required_roles) > 0:
                for role in after.roles:
                    if role in required_roles:
                        break
                else:
                    await after.remove_roles(verification_role, reason='Verified, lost required role')
        else:
            if len(required_roles) > 0:
                for role in after.roles:
                    if role in required_roles:
                        after.add_roles(verification_role, reason='Verified, picked up required role')
                        return
            else:
                await after.add_roles(verification_role, reason='Verified')


@bot.event
async def on_guild_join(guild):
    """Setup DB for guild"""
    async with bot.conn.cursor() as cursor:
        # Checking if guild exists
        g = await (await cursor.execute("SELECT id FROM guilds WHERE id = ?", guild.id)).fetchone()
        if g is None:
            await cursor.execute("INSERT INTO guilds VALUES (?, ?, ?)", (guild.id, None, None))
            await bot.conn.commit()


@bot.event
async def on_command_error(ctx, error):
    """
    Default error handling for the bot

    :param ctx: context object
    :param error: error
    """
    if isinstance(error, commands.CheckFailure) or isinstance(error, commands.MissingPermissions):
        print("!ERROR! " + str(ctx.author.id) + " did not have permissions for " + ctx.command.name + " command")
    elif isinstance(error, commands.BadArgument):
        argument = list(ctx.command.clean_params)[len(ctx.args[2:] if ctx.command.cog else ctx.args[1:])]
        await ctx.send("Could not find the " + argument)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(ctx.command.name + " is missing arguments")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("Bot is missing permissions.")
    else:
        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


# Functions
async def guild_check():
    """
    Check for new guilds and add them to the DB
    """
    async with bot.conn.cursor() as cursor:
        for guild in bot.guilds:
            # Checking if guild exists
            g = await (await cursor.execute("SELECT id FROM guilds WHERE id = ?", guild.id)).fetchone()
            if g is None:
                await cursor.execute("INSERT INTO guilds VALUES (?, ?, ?)", (guild.id, None, None))
                await bot.conn.commit()


# Run the bot
async def main():
    bot.conn = await asqlite.connect('verifications.db')

    # Check if tables exist and create if not
    async with bot.conn.cursor() as cursor:

        # Checking if user table exists
        users = await cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='users'")
        if (await users.fetchone())[0] < 1:
            await cursor.execute("CREATE TABLE users (home_id integer, discord_id text)")
            print('Created users table')

        # Checking if guild table exists
        guilds = await cursor.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='guilds'")
        if (await guilds.fetchone())[0] < 1:
            await cursor.execute("CREATE TABLE guilds (id integer, verification_role integer, required_roles text)")
            print('Created guild table')

        await bot.conn.commit()

        async with aiohttp.ClientSession() as session:
            update_wpi_verifications.start()

            async with bot:
                bot.session = session
                try:
                    discord.utils.setup_logging()
                    await bot.start(os.environ['DISCORD_TOKEN'])
                except KeyboardInterrupt:
                    await bot.session.close()
                    await bot.conn.close()
                    await bot.close()


asyncio.run(main())

