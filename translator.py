import logging
import discord

LOGGER = logging.getLogger(__name__)


class Translator:
    def __init__(self, translations=None):
        if translations is None:
            translations = {}
        self.translations = translations

    def translate(self, message, locale: discord.Locale) -> str:
        LOGGER.debug(f"trying to translate: {message}, {locale}")

        translated = self.translations.get(message, {}).get(locale)

        if translated:
            return translated

        return self.translations.get(message, {}).get(discord.Locale.american_english) or message

    def translate_interaction(self, msg: str, ctx: discord.Interaction) -> str:
        return self.translate(msg, ctx.locale)
