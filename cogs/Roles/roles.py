import logging

import discord
from discord import app_commands
from discord.app_commands import locale_str
from discord.ext import commands
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload, selectinload

from bot import Bot
from translator import Translator
from utils.errors import TransformerMessageNotFound, TransformerNotBotMessage
from utils.transformers import BotMessageTransformer
from . import models, views
from .views import get_ordered_components, RolesEditorBase

from .translations import translations

LOGGER = logging.getLogger(__name__)
_ = Translator(translations).translate_interaction


class Roles(commands.Cog):
    roles = app_commands.Group(
        name=locale_str("roles"),
        description="Create and manage role selection menus",
        default_permissions=discord.Permissions(manage_roles=True),
    )

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.persistent_layouts_loaded = False

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Load the persistent Views once, when the guild data is loaded in the bot."""

        if not self.persistent_layouts_loaded:
            await self.load_persistent_layouts()  # needs guild data, so we load this here
            self.persistent_layouts_loaded = True

    async def load_persistent_layouts(self) -> None:
        """Load all persistent Views."""

        for view_model in await self._get_all_layouts():
            if view_model.channel_id and view_model.message_id:
                view = views.RolesView_Normal(components=get_ordered_components(view_model.components))

                self.bot.add_view(
                    view,
                    message_id=int(view_model.message_id),
                )

    async def layout_id_autocomplete(
            self,
            interaction: discord.Interaction,
            current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for view IDs."""
        async with self.bot.db.session() as session:
            async with session.begin():
                results = (await session.scalars(
                    select(models.Layout).where(models.Layout.guild_id == interaction.guild_id,
                                                models.Layout.id.contains(current))
                )).all()
                choices = [
                    app_commands.Choice(name=f"{view.id} ({'sent' if view.message_id else 'not sent'})", value=view.id)
                    for view in results if str(current) in view.id
                ]
                return choices[:25]

    @roles.command(name=locale_str("setup"))
    async def roles_setup(self, interaction: discord.Interaction) -> None:
        assert isinstance(interaction.user, discord.Member)

        async with self.bot.db.session() as session:
            len_layout_models = await session.scalar(
                select(func.count()).select_from(models.Layout)
                .where(models.Layout.guild_id == interaction.guild_id)
            )

            if len_layout_models >= 2:
                await interaction.response.send_message(
                    _('roles_setup_limit', interaction),
                    ephemeral=True
                )
                return

        preview_layout = views.RolesView_Preview(
            old_class=RolesEditorBase(author=interaction.user, cog=self, components=[], locale=interaction.locale))
        await interaction.response.send_message(_('roles_preview_mode', interaction), view=preview_layout)

    @roles.command(name=locale_str("edit"))
    @app_commands.describe(
        layout_id="The id of the view to edit."
    )
    @app_commands.autocomplete(layout_id=layout_id_autocomplete)
    async def roles_edit(
            self,
            interaction: discord.Interaction,
            layout_id: str = None,
    ) -> None:
        """Edit the content of a role selection menu message."""
        if not layout_id:
            async with self.bot.db.session() as session:
                view_models = (await session.scalars(
                    select(models.Layout)
                    .where(models.Layout.guild_id == interaction.guild_id)
                    .options(
                        selectinload(models.Layout.components).selectinload(models.Component.roles),
                    )
                )).all()

                if not view_models:
                    await interaction.response.send_message(
                        _('roles_no_layouts', interaction),
                        ephemeral=True
                    )
                    return
                select_layout_view = views.SelectLayoutView(views=view_models)

                msg = _('roles_select_edit', interaction) + "\n"
                for idx, view in enumerate(view_models):
                    if view.channel_id and view.message_id:
                        msg += f"{idx}. https://discord.com/channels/{view.guild_id}/{view.channel_id}/{view.message_id}: {view.id}\n"
                    else:
                        msg += f"{idx}. (not sent yet) {view.id}\n"

                await interaction.response.send_message(msg, view=select_layout_view)

                await select_layout_view.wait()
                selected_layout = select_layout_view.selected_layout
        else:
            async with self.bot.db.session() as session:
                selected_layout = await session.scalar(
                    select(models.Layout)
                    .where(models.Layout.id == layout_id, models.Layout.guild_id == interaction.guild_id)
                    .options(
                        selectinload(models.Layout.components).selectinload(models.Component.roles),
                    )
                )

                if selected_layout is None:
                    await interaction.response.send_message(
                        _('roles_layout_not_found', interaction).format(layout_id),
                        ephemeral=True
                    )
                    return

        preview_view = views.RolesView_Preview(
            RolesEditorBase(author=interaction.user, cog=self, layout_id=selected_layout.id,
                            components=get_ordered_components(selected_layout.components), locale=interaction.locale))
        if interaction.response.is_done():
            await interaction.edit_original_response(content=_('roles_preview_mode', interaction), view=preview_view)
        else:
            await interaction.response.send_message(content=_('roles_preview_mode', interaction), view=preview_view)

    delete = app_commands.Group(name=locale_str("delete"), description="Delete roles menu or message", parent=roles)

    @delete.command(name=locale_str("layout"))
    @app_commands.describe(
        layout_id="The id of the view to edit."
    )
    @app_commands.autocomplete(layout_id=layout_id_autocomplete)
    async def roles_delete_layout(
            self,
            interaction: discord.Interaction,
            layout_id: str = None,
    ) -> None:

        async with self.bot.db.session() as session:
            async with session.begin():
                view_model = await session.scalar(
                    select(models.Layout).where(models.Layout.id == layout_id,
                                                models.Layout.guild_id == interaction.guild_id)
                )

                if view_model is None:
                    await interaction.response.send_message(
                        _('roles_layout_not_found', interaction).format(layout_id),
                        ephemeral=True
                    )
                    return

                if view_model.channel_id and view_model.message_id:
                    try:
                        channel = interaction.guild.get_channel(int(view_model.channel_id))
                        if channel is None:
                            raise ValueError("Channel not found in guild.")
                        message = await BotMessageTransformer().transform(
                            interaction, f"{view_model.channel_id}-{view_model.message_id}"
                        )
                        await message.delete()
                    except (TransformerMessageNotFound, TransformerNotBotMessage, ValueError) as e:
                        logging.warning(
                            f"Could not delete message {view_model.message_id} in channel {view_model.channel_id}: {e}")
                        pass

                await session.delete(view_model)

        await interaction.response.send_message(
            _('roles_layout_deleted', interaction).format(layout_id),
            ephemeral=True
        )

    @delete.command(name=locale_str("message"))
    @app_commands.describe(
        message="Link or ID of the message to remove. Must be the bot's!"
    )
    async def roles_delete_msg(self, interaction: discord.Interaction,
                               message: app_commands.Transform[discord.Message, BotMessageTransformer]) -> None:
        """Delete a role selection menu message.(The view will still be saved in the database.)"""
        assert isinstance(message.channel, discord.abc.GuildChannel)

        async with self.bot.db.session() as session:
            async with session.begin():
                view_model = await session.scalar(
                    select(models.Layout).where(models.Layout.message_id == message.id,
                                                models.Layout.guild_id == interaction.guild_id)
                )

                if view_model is not None:
                    view_model.message_id = None
                    view_model.channel_id = None
                    await session.commit()
                else:
                    logging.warning(f"Message {message.id} not found in database.")
                    await interaction.response.send_message(
                        _('roles_msg_not_found', interaction),
                        ephemeral=True
                    )
                    return

        await message.delete()

        await interaction.response.send_message(
            _('roles_msg_deleted', interaction),
            ephemeral=True
        )

    @roles.command(name=locale_str("send"))
    @app_commands.describe(
        layout_id="The id of the view.",
        channel="The channel to send the message.",
    )
    @app_commands.autocomplete(layout_id=layout_id_autocomplete)
    async def roles_send(self, interaction: discord.Interaction, layout_id: str,
                         channel: discord.TextChannel | None = None) -> None:

        async with self.bot.db.session() as session:
            view_model: models.Layout = await session.scalar(
                select(models.Layout)
                .where(models.Layout.id == layout_id, models.Layout.guild_id == interaction.guild_id)
                .options(
                    joinedload(models.Layout.components).joinedload(models.Component.roles),
                )
            )

            if view_model is None:
                await interaction.response.send_message(
                    _('roles_layout_not_found', interaction).format(layout_id),
                    ephemeral=True
                )
                return

            if channel is None:
                channel = interaction.channel

            components = get_ordered_components(view_model.components)
            logging.debug(components)
            view = views.RolesView_Normal(components=components, locale=interaction.guild.preferred_locale)

            message = await channel.send(view=view)

            view_model.channel_id = channel.id
            view_model.message_id = message.id
            await session.commit()

            await interaction.response.send_message(
                _('roles_msg_sent', interaction),
                ephemeral=True
            )

    @roles_edit.error
    async def roles_error(
            self, interaction: discord.Interaction, error: Exception
    ) -> None:
        """Error handler for the roles subcommands."""

        if isinstance(error, TransformerMessageNotFound):
            msg = "{0} ({1})\nYou might need to use the format `{channel ID}-{message ID}` (shift-clicking on \"Copy ID\") or the message URL.".format(
                error, error.original)
            await interaction.response.send_message(msg, ephemeral=True)

        elif isinstance(error, TransformerNotBotMessage):
            await interaction.response.send_message(
                "Cannot delete message. {0}".format(error),
                ephemeral=True
            )

        else:
            interaction.extras["error_handled"] = False

    async def _get_all_layouts(self) -> list[models.Layout]:
        """Select all registered Views from the database."""
        async with self.bot.db.session() as session:
            roles_layout_models = await session.scalars(
                select(models.Layout).options(
                    joinedload(models.Layout.components),
                    joinedload(models.Layout.components).joinedload(models.Component.roles),
                )
            )

        return list(roles_layout_models.unique())
