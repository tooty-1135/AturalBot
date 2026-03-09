import discord
from discord import Interaction
from discord.ui import View, Button, Select
from sqlalchemy import select

from . import models


class DvcState:
    locked: bool = False
    user_limit: int = 0


class DvcRenameModal(discord.ui.Modal, title="Rename DVC"):
    def __init__(self, cog, locale: discord.Locale = None):
        super().__init__()
        self.cog = cog
        self.locale = locale

        self.name_input = discord.ui.TextInput(
            label="New Channel Name",
            placeholder="Enter the new name for your voice channel",
            min_length=1,
            max_length=100,
        )
        self.add_item(self.name_input)

    async def on_submit(self, interaction: discord.Interaction):
        async with self.cog.bot.db.session() as session:
            voice_id: models.VoiceChannel.voice_id = await session.scalar(
                select(models.VoiceChannel.voice_id)
                .where(models.VoiceChannel.user_id == interaction.user.id)
            )

            if voice_id is None:
                await interaction.response.edit_message(content='語音頻道已刪除')
                return

            channel = self.cog.bot.get_channel(voice_id)
            await channel.edit(name=self.name_input.value)
            await interaction.response.defer()


class DvcControlBase(View):
    """Base view for DVC control commands."""

    def __init__(self, author: discord.Member, state: DvcState, cog, locale: discord.Locale = None):
        super().__init__()
        self.author = author
        self.state = state
        self.cog = cog
        self.locale = locale

    # 我不確定interaction_check能不能用response
    async def interaction_check(self, interaction: Interaction, /) -> bool:
        async with self.cog.bot.db.session() as session:
            voice_id: models.VoiceChannel.voice_id = await session.scalar(
                select(models.VoiceChannel.voice_id)
                .where(models.VoiceChannel.user_id == interaction.user.id)
            )

            if voice_id is None:
                await interaction.response.send_message('語音頻道已刪除', ephemeral=True)
                return False
            else:
                if interaction.user.id != self.author.id:
                    await interaction.response.send_message('只有頻道擁有者可以使用此操作', ephemeral=True)
                    return False
                return True


class DvcSetLimitModal(discord.ui.Modal, title="Set User Limit"):
    def __init__(self, cog, locale: discord.Locale = None):
        super().__init__()
        self.cog = cog
        self.locale = locale

        self.limit_input = discord.ui.TextInput(
            label="User Limit",
            placeholder="Enter the maximum number of users allowed in your voice channel (0 for no limit)",
            min_length=1,
            max_length=3,
        )
        self.add_item(self.limit_input)

    async def on_submit(self, interaction: discord.Interaction):
        limit = int(self.limit_input.value)
        if limit < 0:
            await interaction.response.send_message('請輸入有效的數字', ephemeral=True)
            return
        if limit > 99:
            await interaction.response.send_message('用戶上限不能超過 99', ephemeral=True)
            return

        async with self.cog.bot.db.session() as session:
            voice_id: models.VoiceChannel.voice_id = await session.scalar(
                select(models.VoiceChannel.voice_id)
                .where(models.VoiceChannel.user_id == interaction.user.id)
            )

            if voice_id is None:
                await interaction.response.send_message('語音頻道已刪除', ephemeral=True)
                return

            channel = self.cog.bot.get_channel(voice_id)
            await channel.edit(user_limit=limit)
            await interaction.response.defer()


class DvcControl(DvcControlBase):
    """View for DVC control commands."""

    def __init__(self, old_view: DvcControlBase):
        super().__init__(old_view.author, old_view.state, old_view.cog, old_view.locale)

        self.lock_select = Select(placeholder="Lock/Unlock DVC", options=[
            discord.SelectOption(label="Locked", value="lock", default=self.state.locked),
            discord.SelectOption(label="Unlocked", value="unlock", default=not self.state.locked),
        ])
        self.lock_select.callback = self.lock_select_callback
        self.add_item(self.lock_select)

        rename_button = Button(label="Rename")
        rename_button.callback = self.rename_callback
        self.add_item(rename_button)

        set_limit_button = Button(label="Set User Limit")
        set_limit_button.callback = self.set_limit_callback
        self.add_item(set_limit_button)

        # whitelist_button = Button(label="Manage Whitelist")
        # self.add_item(whitelist_button)
        #
        # blacklist_button = Button(label="Manage Blacklist")
        # self.add_item(blacklist_button)

        delete_button = Button(label="Delete", style=discord.ButtonStyle.danger)
        self.add_item(delete_button)

    async def lock_select_callback(self, interaction: discord.Interaction):
        async with self.cog.bot.db.session() as session:
            voice_id: models.VoiceChannel.voice_id = await session.scalar(
                select(models.VoiceChannel.voice_id)
                .where(models.VoiceChannel.user_id == interaction.user.id)
            )

            role = interaction.guild.default_role
            channel = self.cog.bot.get_channel(voice_id)

            selected_value = self.lock_select.values[0]
            if selected_value == "lock":
                await channel.set_permissions(role, connect=False)
                self.state.locked = True
            elif selected_value == "unlock":
                await channel.set_permissions(role, connect=True)
                self.state.locked = False
            await session.commit()
            await interaction.response.defer()

    async def rename_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(DvcRenameModal(self.cog, self.locale))

    async def set_limit_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(DvcSetLimitModal(self.cog, self.locale))
