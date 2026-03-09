import logging
from typing import Union

import discord
from discord import app_commands
from discord.app_commands import locale_str
from discord.ext import commands

from bot import Bot
from translator import Translator
from utils import relative_dt, run_process

from .translations import translations

LOGGER = logging.getLogger(__name__)

_ = Translator(translations).translate_interaction


def int_fmt(number, digits=3):
    return f"`{number:>{digits}d}`"


class Information(commands.Cog):
    info = app_commands.Group(
        name=locale_str("info"), description=locale_str("info_about_sth")
    )

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        self.info_user_context_menu = app_commands.ContextMenu(
            name=locale_str("info_ctx"),
            callback=self.info_user_callback,
        )
        self.bot.tree.add_command(self.info_user_context_menu)

    @app_commands.command(name=locale_str("about_bot"), description=locale_str("about_this_bot"))
    async def about(self, interaction: discord.Interaction):
        """View information about the bot itself."""

        assert self.bot.user is not None
        assert interaction.guild is not None
        app_info = await self.bot.application_info()

        if self.bot.user.avatar:
            thumbnail_url = self.bot.user.avatar.url
        else:
            thumbnail_url = ""

        embed = discord.Embed(
            title=_("info_about_bot", interaction) % self.bot.user,
            description=app_info.description,
            color=discord.Color.blurple(),
        ).set_thumbnail(url=thumbnail_url)

        # some statistics
        total_members = len(self.bot.users)

        text_channels = 0
        voice_channels = 0
        guilds = 0
        for guild in self.bot.guilds:
            guilds += 1
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    text_channels += 1
                elif isinstance(channel, discord.VoiceChannel):
                    voice_channels += 1

        embed.add_field(
            name=_("Members", interaction),
            value=_("total_members", interaction) % int_fmt(total_members),
        )
        embed.add_field(
            name=_("channels", interaction),
            value=(
                _("total_channels", interaction) % int_fmt(text_channels + voice_channels) + "\n"
                + _("text_channels", interaction) % int_fmt(text_channels) + "\n"
                + _("voice_channels", interaction) % int_fmt(voice_channels)
            ),
        )
        embed.add_field(
            name=_("installs", interaction),
            value=(
                _("servers_count", interaction) % int_fmt(app_info.approximate_guild_count) + "\n"
                + _("users_count", interaction) % int_fmt(app_info.approximate_user_install_count)
            ),
        )
        embed.add_field(
            name=_("timeline", interaction),
            value=(
                _("created_at", interaction) % relative_dt(self.bot.user.created_at) + "\n"
                + _("joined_at", interaction) % relative_dt(interaction.guild.me.joined_at or discord.utils.utcnow()) + "\n"
                + _("boot_time", interaction) % relative_dt(self.bot.boot_time)
            ),
            inline=False,
        )

        embed.set_footer(
            text=_("made_with", interaction) % (discord.__version__, app_info.owner),
            icon_url="http://i.imgur.com/5BFecvA.png",
        )
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @info.command(name=locale_str("server"), description=locale_str("info_about_server"))
    async def info_guild(self, interaction: discord.Interaction):
        """View information about the current server."""

        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message(
                "Cannot use this command in private messages.", ephemeral=True
            )

        embed = discord.Embed(title=guild.name, color=discord.Color.blurple())
        description = _("server_created", interaction) % relative_dt(guild.created_at)
        if guild.description:
            description = f"{guild.description}\n{description}"
        embed.description = description

        embed.set_thumbnail(
            url=(
                guild.icon.url
                if guild.icon
                else "https://cdn.discordapp.com/embed/avatars/1.png"
            )
        )

        embed.add_field(
            name=_("members_info", interaction),
            value=(
                _("total_members_count", interaction) % int_fmt(guild.member_count) + "\n"
                + _("roles_count", interaction) % int_fmt(len(guild.roles) - 1)
            ),
        ).add_field(
            name=_("nitro_level", interaction) % guild.premium_tier,
            value=(
                _("nitro_boosters", interaction) % int_fmt(len(guild.premium_subscribers)) + "\n"
                + _("nitro_boosts", interaction) % int_fmt(guild.premium_subscription_count)
            ),
        ).add_field(
            name=_("server_channels", interaction),
            value=(
                _("text_channels_count", interaction) % int_fmt(len(guild.text_channels)) + "\n"
                + _("voice_channels_count", interaction) % int_fmt(len(guild.voice_channels)) + "\n"
                + _("stage_channels_count", interaction) % int_fmt(len(guild.stage_channels))
            ),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @info.command(name=locale_str("user"), description="info_about_user")
    @app_commands.describe(user="User or member to get the information of")
    async def info_user(
            self,
            interaction: discord.Interaction,
            user: Union[discord.Member, discord.User],
    ):
        """View information about a user / member."""

        await self.info_user_callback(interaction, user)

    async def info_user_callback(
            self,
            interaction: discord.Interaction,
            user: Union[discord.Member, discord.User],
    ):
        """Send the information about the requested user / member."""

        application_emojis = await self.bot.fetch_application_emojis()

        def get_badge_emoji(badge: str) -> discord.Emoji | None:
            for emoji in application_emojis:
                if emoji.name == badge:
                    return emoji

            return None

        badges = []
        emoji_warning = []
        for badge, is_set in user.public_flags:
            if not is_set:
                # skip if the flag is not set: the user does not have the badge
                continue

            emoji = get_badge_emoji(badge)
            if emoji is not None:
                badges.append(str(emoji))
            else:
                emoji_warning.append(badge)

        if len(emoji_warning) != 0:
            warning_str = ", ".join(emoji_warning)
            LOGGER.warning(
                "Some Application Emoji were not found, they will not show on profile: "
                f"{warning_str}"
            )
            LOGGER.warning(
                "Download the files at https://emoji.gg/pack/1834-profile-badges# "
                "and name them according to discord.User.public_flags"
            )

        embed = (
            discord.Embed(
                title=f"{user}", description=" ".join(badges), color=user.color
            )
            .add_field(
                name=_("user_info", interaction),
                value=(
                    _("user_created", interaction) % relative_dt(user.created_at) + "\n"
                    + _("user_profile", interaction) % user.mention + "\n"
                    + f"ID: {user.id}"
                ),
                inline=False,
            )
            .set_thumbnail(url=user.avatar.url if user.avatar else None)
        )

        if isinstance(user, discord.Member):
            # we have more information here
            embed.title = f"{user.display_name} ({user})"
            embed.add_field(
                name=_("member_info", interaction),
                value=(
                    (_("member_joined", interaction) % relative_dt(user.joined_at) if user.joined_at else _("Unknown", interaction)) + "\n"
                    + _("member_roles", interaction) % ", ".join(r.mention for r in reversed(user.roles[1:]))
                ),
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)
