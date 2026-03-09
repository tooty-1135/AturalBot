# !/usr/bin/python
# coding:utf-8
import logging
import os

import discord
import dotenv
from discord import app_commands

from bot import Bot

root_logger = logging.getLogger()
logging.basicConfig(level=logging.DEBUG)

dotenv.load_dotenv('.env')

owners = [881312396784840744]
extensions = [
    "CommandTranslator",
    # "Information",
    # "Roles",
    # "DVC",
    "Ticket",
]
intents = discord.Intents().all()
intents.presences = False
activity = discord.Activity(type=discord.ActivityType.playing, name="…什麼東西")

bot = Bot(activity=activity,
          owner_ids=set(owners),
          intents=intents,
          command_prefix=[],
          startup_extensions=extensions,
          db_name="s179_AturalBot_Test")


def is_owner(interaction: discord.Interaction) -> bool:
    return interaction.user.id in owners


bot.is_owner = is_owner  # TODO: 整合


@bot.tree.command()
@app_commands.check(is_owner)
async def reload(interaction: discord.Interaction, cog: str) -> None:
    await bot.reload_extension("cogs." + cog)
    await interaction.response.send_message(f"重新載入{cog}完成!", ephemeral=True)
    await bot.tree.sync()


@bot.tree.command()
@app_commands.check(is_owner)
async def load(interaction: discord.Interaction, cog: str) -> None:
    await bot.load_extension("cogs." + cog)
    await interaction.response.send_message(f"載入{cog}完成!", ephemeral=True)
    await bot.tree.sync()


@bot.tree.command()
@app_commands.check(is_owner)
async def unload(interaction: discord.Interaction, cog: str) -> None:
    await bot.unload_extension("cogs." + cog)
    await interaction.response.send_message(f"卸載{cog}完成!", ephemeral=True)
    await bot.tree.sync()


bot.run(os.getenv('BOT_TOKEN'))
