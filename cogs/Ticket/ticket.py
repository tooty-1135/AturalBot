import discord

from bot import Bot
from discord import app_commands, Embed
from discord.ext import commands
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload, selectinload

from . import models, views
from .views import ticket_creation_embed


async def category_list_embed():
    embed = discord.Embed(title="Ticket Categories(1/3)",
                          description="[upgrade](https://owo.owo)")

    embed.add_field(name="",
                    value="```1. Support```",
                    inline=False)
    embed.add_field(name="",
                    value="```2. Giveaway```",
                    inline=False)

    embed.set_footer(text="AturalBot")


def edit_category_embed(name: str, cat_name: str, msg_channel: str = None, edit: bool = True):
    embed = discord.Embed(title="Edit Category" if edit else "Create Category")

    embed.add_field(name="Name",
                    value=name,
                    inline=False)
    embed.add_field(name="Category",
                    value=cat_name,)
    embed.add_field(name="Send message at",
                    value=cat_name,
                    inline=False)

    embed.set_footer(text="AturalBot")

    return embed


class Ticket(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.persistent_layouts_loaded = False

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Load the persistent Views once, when the guild data is loaded in the bot."""

        if not self.persistent_layouts_loaded:
            await self.load_create_buttons()
            await self.load_ticket_buttons()
            self.persistent_layouts_loaded = True

    async def load_create_buttons(self):
        async with self.bot.db.session() as session:
            # Ticket Creation Views
            category_msgs = await session.scalars(
                select(models.Category)
            )

            for category in category_msgs:
                if category:
                    view_settings = views.TicketCreationSettings(category_id=category.category_id)
                    view = views.TicketCreation(settings=view_settings, cog=self, locale=None) #TODO: get guild locale

                    self.bot.add_view(
                        view,
                        message_id=int(category.message_id),
                    )

            # Ticket Views
            tickets = await session.scalars(
                select(models.Ticket)
            )

            for ticket in tickets:
                if ticket:
                    view_settings = views.TicketManagementSettings(owner_id=ticket.owner_id, ticket_id=ticket.id)
                    view = views.TicketManagement(settings=view_settings, cog=self, locale=None) #TODO: get guild locale

                    self.bot.add_view(
                        view,
                        message_id=int(category.message_id),
                    )



    ticket = app_commands.Group(
        name="ticket",
        description="Create a private channel",
        default_permissions=discord.Permissions(manage_channels=True),
    )

    @ticket.command(name="setup")
    async def setup(self, interaction: discord.Interaction):
        async with self.bot.db.session() as session:
            len_layout_models = await session.scalar(
                select(func.count()).select_from(models.Category)
                .where(models.Category.guild_id == interaction.guild_id)
            )

            if len_layout_models >= 2:
                await interaction.response.send_message(
                    "Max category number reached(2/2)",
                    ephemeral=True
                )
                return

        view = views.CreateCategory(author=interaction.user, cog=self, locale=interaction.locale)
        view.cat_name = "Ticket"
        embed = ticket_creation_embed(name=view.cat_name)
        await interaction.response.send_message(f"Previewing... click Save button to apply.", embed=embed, view=view)
