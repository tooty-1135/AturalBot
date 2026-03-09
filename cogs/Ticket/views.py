from fileinput import close

import discord
from discord import ButtonStyle
from discord.ui import View, Select, Button, ChannelSelect, Modal, TextInput
from sqlalchemy import select
from sqlalchemy.util import await_only

from utils.views import interaction_defer
from . import models

def ticket_creation_embed(name="Ticket", description="Click the button to create a ticket", image=None):
    embed = discord.Embed(title=name, description=description)

    embed.set_image(url=image)

    embed.set_footer(text="AturalBot",
                     icon_url="https://media.discordapp.net/attachments/908854588294197328/1476796661417115689/avatar.png?ex=69a26d91&is=69a11c11&hm=2dbdb50fc7ef9665cc8a0ea6bfe2a918d06ff929b6f1dd4b2c3a729d1cf49e36&=&format=webp&quality=lossless&width=1050&height=1050")

    return embed

class TicketCreationSettings:
    def __init__(self, category_id):
        self.category_id = category_id

class TicketCreation(View):
    def __init__(self, settings: TicketCreationSettings, cog, locale: discord.Locale = None):
        super().__init__(timeout=None)
        self.cog = cog
        self.locale = locale
        self.settings = settings

        button = Button(label="Create Ticket", custom_id="create_ticket", style=ButtonStyle.green)
        button.callback = self.create_callback
        self.add_item(button)


    async def create_callback(self, interaction: discord.Interaction):
        async with self.cog.bot.db.session() as session:
            db_category: models.Category = await session.scalar(
                select(models.Category.name, models.Category.guild_id)
                .where(models.Category.category_id == self.settings.category_id)
            )
            if db_category is None:
                await interaction.response.send_message("This category is not configured, please contact the administrator.", ephemeral=True)
                return

            category = self.cog.bot.get_channel(self.settings.category_id)
            if category is None or not isinstance(category, discord.CategoryChannel):
                await interaction.response.send_message("The bot can't reach the category, please contact the administrator.", ephemeral=True)
                return

            ticket_channel = await category.create_text_channel(name=f"ticket-{interaction.user.name}", reason="Ticket created")
            await ticket_channel.set_permissions(interaction.guild.default_role, view_channel=False)
            await ticket_channel.set_permissions(interaction.user, view_channel=True, send_messages=True)

            await interaction.response.send_message(f"Ticket created: {ticket_channel.mention}", ephemeral=True)

            #TODO: Buttons for closing, claiming, etc.
            await ticket_channel.send(f"{interaction.user.mention} This is your ticket channel, please describe your issue in detail and wait for the staff to assist you.")

            db_ticket = models.Ticket(
                owner_id=interaction.user.id,
                channel_id=ticket_channel.id,
                category_id=self.settings.category_id
            )
            session.add(db_ticket)
            await session.commit()


class TicketManagementSettings:
    def __init__(self, ticket_id, owner_id):
        self.ticket_id = ticket_id
        self.owner_id = owner_id

class TicketManagement(View):
    def __init__(self, settings: TicketManagementSettings, cog, locale: discord.Locale = None):
        super().__init__(timeout=None)
        self.cog = cog
        self.locale = locale
        self.settings = settings

        close_btn = Button(label="Close Ticket", style=ButtonStyle.red)
        close_btn.callback = self.close_ticket
        self.add_item(close_btn)

    async def close_ticket(self, interaction: discord.Interaction):
        async with self.cog.bot.db.session() as session:
            db_ticket: models.Ticket = await session.scalar(
                select(models.Ticket)
                .where(models.Ticket.id == self.settings.ticket_id)
            )
            if db_ticket is None:
                await interaction.response.send_message("This ticket is not found in the database, please contact the administrator.", ephemeral=True)
                return

            channel = self.cog.bot.get_channel(db_ticket.channel_id)
            if channel is None or not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message("The bot can't reach the ticket channel, please contact the administrator.", ephemeral=True)
                return

            await channel.delete(reason="Ticket closed")

            await session.delete(db_ticket)
            await session.commit()

class CreateCategory_SetName(Modal, title="Edit category name"):
    cat_name:str

    def __init__(self, locale: discord.Locale = None):
        super().__init__()

        self.name_field = TextInput(label="Name", placeholder="Name")
        self.add_item(self.name_field)

    async def on_submit(self, interaction: discord.Interaction):
        self.cat_name = self.name_field.value
        await interaction.response.defer()

class TicketBase(View):
    def __init__(self, settings, author: discord.Member, cog, locale: discord.Locale = None):
        super().__init__()
        self.author = author
        self.cog = cog
        self.locale = locale
        self.settings = settings

class ManageCategoriesBase(View):
    def __init__(self, settings, author: discord.Member, cog, locale: discord.Locale = None):
        super().__init__()
        self.author = author
        self.cog = cog
        self.locale = locale
        self.settings = settings

class CreateCategory(View):
    cat_name:str

    def __init__(self, author: discord.Member, cog, locale: discord.Locale = None):
        super().__init__()
        self.author = author
        self.cog = cog
        self.locale = locale
        self.settings = models.Category()

        self.category_select = Select(placeholder="Select a category", max_values=1)
        self.category_select.callback = interaction_defer
        # get categories
        for cate in author.guild.categories:
            self.category_select.add_option(label=cate.name, value=str(cate.id))
        self.add_item(self.category_select)

        self.send_msg_channel = ChannelSelect(placeholder="Select a channel", max_values=1)
        self.send_msg_channel.callback = interaction_defer
        self.add_item(self.send_msg_channel)

        set_name_btn = Button(label="Set name", style=ButtonStyle.blurple)
        set_name_btn.callback = self.change_name
        self.add_item(set_name_btn)

        save_btn = Button(label="Save", style=ButtonStyle.green)
        save_btn.callback = self.save_category
        self.add_item(save_btn)

        cancel_btn = Button(label="Cancel", style=ButtonStyle.red)
        cancel_btn.callback = self.cancel
        self.add_item(cancel_btn)

    async def change_name(self, interaction:discord.Interaction):
        set_name_modal = CreateCategory_SetName(locale=self.locale)
        await interaction.response.send_modal(set_name_modal)
        await set_name_modal.wait()
        self.cat_name = set_name_modal.cat_name

        await interaction.message.edit(embed=ticket_creation_embed(name=self.cat_name))

    async def save_category(self, interaction: discord.Interaction):
        async with self.cog.bot.db.session() as session:
            db_category: models.Category = await session.scalar(
                select(models.Category.category_id)
                .where(models.Category.category_id == self.category_select.values[0])
            )

            if db_category:
                await interaction.response.send_message("A config with this category already exist, please select another", ephemeral=True)
                return

            channel = self.send_msg_channel.values[0].resolve()
            if not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message("Please select a text channel", ephemeral=True)
                return

            embed = ticket_creation_embed(name=self.cat_name)

            view_settings = TicketCreationSettings(category_id=self.category_select.values[0])
            view = TicketCreation(settings=view_settings, cog=self.cog, locale=self.locale)

            message = await channel.send(embed=embed, view=view)

            db_guild = models.Category(
                name=self.cat_name,
                guild_id=interaction.guild.id,
                category_id=self.category_select.values[0],
                message_id=message.id
            )
            session.add(db_guild)
            await session.commit()

            await interaction.response.edit_message(content="Saved.", embed=None, view=None)

    async def cancel(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="canceled", embed=None, view=None)
        self.stop()
