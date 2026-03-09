import logging

import discord
from discord import app_commands

from .translations import translations

LOGGER = logging.getLogger(__name__)


class CommandTranslator(app_commands.Translator):
    async def translate(
            self,
            string: app_commands.locale_str,
            locale: discord.Locale,
            context: app_commands.TranslationContext
    ) -> str | None:
        translated = translations.get(context.location, {}).get(string.message, {}).get(locale)

        if translated:
            return translated

        return translations.get(context.location, {}).get(string.message, {}).get(discord.Locale.american_english)
