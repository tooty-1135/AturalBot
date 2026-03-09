from bot import Bot
from .translator import CommandTranslator


async def setup(bot: Bot):
    await bot.tree.set_translator(CommandTranslator())

async def teardown(bot: Bot):
    await bot.tree.set_translator(None)
