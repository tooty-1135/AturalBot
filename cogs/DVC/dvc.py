import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from bot import Bot
from sqlalchemy import select
from . import views, models


class setup_modal(discord.ui.Modal, title='Setup Dynamic Voice Channel'):
    def __init__(self, bot: Bot):
        self.bot = bot
        super().__init__()

    ca_id = discord.ui.TextInput(label='類別ID', placeholder="1128923701455360146")
    ch_id = discord.ui.TextInput(label='頻道ID', placeholder="1129012268814835782")

    async def on_submit(self, interaction: discord.Interaction):
        category = self.bot.get_channel(int(self.ca_id.value))
        channel = self.bot.get_channel(int(self.ch_id.value))

        if not isinstance(category, discord.CategoryChannel) or not isinstance(channel, discord.VoiceChannel):
            await interaction.response.send_message("無效的類別ID或頻道ID。請確認它們是正確的類型。", ephemeral=True)
            return

        async with self.bot.db.session() as session:
            db_guild: models.Guild = await session.scalar(
                select(models.Guild)
                .where(models.Guild.guild_id == interaction.guild.id)
            )

            if not db_guild:
                db_guild = models.Guild(
                    guild_id=interaction.guild.id,
                    owner_id=interaction.user.id,
                )
                session.add(db_guild)

            db_guild.voice_channel_id = channel.id
            db_guild.voice_category_id = category.id
            await session.commit()

            await interaction.response.edit_message(content="動態語音頻道設定完成")


# class setup_modal(discord.ui.Modal, title='Setup Dynamic Voice Channel'):
#     ca_name = discord.ui.TextInput(label='類別名稱：（例如:語音頻道）', default="語音頻道")
#     ch_name = discord.ui.TextInput(label='頻道名稱 : (例如:按我創建語音頻道)', default="按我創建語音頻道")
#
#     async def on_submit(self, interaction: discord.Interaction):
#         conn = sqlite3.connect('datas/voice/voice.db')
#         c = conn.cursor()
#         new_cat = await interaction.guild.create_category_channel(str(self.ca_name))
#         guildID = interaction.guild.id
#         id = interaction.user.id
#
#         channel = await interaction.guild.create_voice_channel(str(self.ch_name), category=new_cat)
#         c.execute("SELECT * FROM guild WHERE guildID = ? AND ownerID=?", (guildID, id))
#         voice = c.fetchone()
#         if voice is None:
#             c.execute("INSERT INTO guild VALUES (?, ?, ?, ?)", (guildID, id, channel.id, new_cat.id))
#         else:
#             c.execute(
#                 "UPDATE guild SET guildID = ?, ownerID = ?, voiceChannelID = ?, voiceCategoryID = ? WHERE guildID = ?",
#                 (guildID, id, channel.id, new_cat.id, guildID))
#         await interaction.response.send_message("**設定完成!**")
#         # except:
#         #    await interaction.response.send_message("糟糕!發生了一些問題")
#
#         conn.commit()
#         conn.close()


class DVC(commands.Cog):
    """動態語音頻道"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        if after.channel:
            async with self.bot.db.session() as session:
                guild = await session.scalar(
                    select(models.Guild)
                    .where(models.Guild.guild_id == member.guild.id)
                )

                if guild:
                    if after.channel.id == guild.voice_channel_id:
                        old_channel = await session.scalar(
                            select(models.VoiceChannel.user_id)
                            .where(models.VoiceChannel.user_id == member.id)
                        )
                        if old_channel:
                            await member.send("創建語音頻道的速度太快了!請等待15秒!")
                            await asyncio.sleep(15)

                        setting: models.UserSettings = await session.scalar(
                            select(models.UserSettings)
                            .where(models.UserSettings.user_id == member.id)
                        )

                        if not setting:
                            name = guild.channel_name_template % member.name
                            limit = 0
                        else:
                            if setting.channel_name:
                                name = setting.channel_name
                            else:
                                name = guild.channel_name_template % member.name
                            limit = setting.channel_max_people

                        category_id = guild.voice_category_id
                        category = self.bot.get_channel(category_id)
                        new_channel = await member.guild.create_voice_channel(name, category=category)
                        await member.move_to(new_channel)
                        await new_channel.set_permissions(self.bot.user, connect=True, read_messages=True)
                        await new_channel.edit(name=name, user_limit=limit)

                        new_channel_db = models.VoiceChannel(
                            user_id=member.id,
                            voice_id=new_channel.id
                        )
                        session.add(new_channel_db)
                        await session.commit()
        else:
            async with self.bot.db.session() as session:
                voice_channel: models.VoiceChannel = await session.scalar(
                    select(models.VoiceChannel)
                    .where(models.VoiceChannel.user_id == member.id)
                )

                if voice_channel:
                    channel = self.bot.get_channel(voice_channel.voice_id)
                    if channel and len(channel.members) == 0:
                        await channel.delete()
                        await asyncio.sleep(3)

                        await session.delete(voice_channel)
                        await session.commit()

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if isinstance(channel, discord.VoiceChannel):
            async with self.bot.db.session() as session:
                voice_channel: models.VoiceChannel = await session.scalar(
                    select(models.VoiceChannel)
                    .where(models.VoiceChannel.voice_id == channel.id)
                )

                if voice_channel:
                    await session.delete(voice_channel)
                    await session.commit()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        async with self.bot.db.session() as session:
            guild_setting: models.Guild = await session.scalar(
                select(models.Guild)
                .where(models.Guild.guild_id == guild.id)
            )

            if guild_setting:
                await session.delete(guild_setting)
                await session.commit()

    dvc = app_commands.Group(name='dvc', description='動態語音頻道')

    @dvc.command()
    @commands.has_permissions(manage_channels=True)
    async def setup(self, interaction: discord.Interaction):
        """初始化動態語音頻道"""

        async with self.bot.db.session() as session:
            db_guild: models.Guild = await session.scalar(
                select(models.Guild)
                .where(models.Guild.guild_id == interaction.guild.id)
            )

            if db_guild:
                view = discord.ui.View()
                button = discord.ui.Button(label="繼續", style=discord.ButtonStyle.danger)
                button.callback = lambda i: i.response.send_modal(setup_modal(self.bot))
                view.add_item(button)
                back = discord.ui.Button(label="返回", style=discord.ButtonStyle.blurple)
                back.callback = lambda i: i.response.edit_message(content="已取消操作", view=None)
                view.add_item(back)

                await interaction.response.send_message("存在舊的設定檔，繼續操作會覆蓋舊的設定",
                                                        view=view, ephemeral=True)
                return

        await interaction.response.send_modal(setup_modal(self.bot))

    @dvc.command()
    async def control(self, interaction: discord.Interaction):
        async with self.bot.db.session() as session:
            voice_id: models.VoiceChannel.voice_id = await session.scalar(
                select(models.VoiceChannel.voice_id)
                .where(models.VoiceChannel.user_id == interaction.user.id)
            )

            if not voice_id:
                await interaction.response.send_message("找不到目標語音頻道，你必須先連接請先加入一個動態頻道", ephemeral=True)
                return

            view = views.DvcControl(views.DvcControlBase(interaction.user, views.DvcState(), self, interaction.locale))
            await interaction.response.send_message(view=view, ephemeral=True)


    @dvc.command()
    async def destroy(self, interaction: discord.Interaction):
        await self.on_guild_remove(interaction.guild)
        await interaction.response.send_message("執行完成")


    # @dvc.command()
    # async def permit(self, interaction: discord.Interaction, member: discord.Member):
    #     """允許某個人進入你的動態語音頻道"""
    #     async with self.bot.db.session() as session:
    #         voice_id: models.VoiceChannel.voice_id = await session.scalar(
    #             select(models.VoiceChannel.voice_id)
    #             .where(models.VoiceChannel.user_id == interaction.user.id)
    #         )
    #
    #     if voice_id is None:
    #         await interaction.response.send_message(f"{interaction.user.mention} 你沒有自己的動態語音頻道")
    #     else:
    #         channel = self.bot.get_channel(voice_id)
    #         await channel.set_permissions(member, connect=True)
    #         await interaction.response.send_message(
    #             f'允許 {member.name} 進入 {interaction.user.mention} 的動態語音頻道 ✅')
    #
    # @dvc.command()
    # async def reject(self, interaction: discord.Interaction, member: discord.Member):
    #     """拒絕某個人進入你的動態語音頻道"""
    #     async with self.bot.db.session() as session:
    #         voice_id: models.VoiceChannel.voice_id = await session.scalar(
    #             select(models.VoiceChannel.voice_id)
    #             .where(models.VoiceChannel.user_id == interaction.user.id)
    #         )
    #
    #     if voice_id is None:
    #         await interaction.response.send_message(f"{interaction.user.mention} 你沒有自己的動態語音頻道")
    #     else:
    #         channel = self.bot.get_channel(voice_id)
    #         for members in channel.members:
    #             if members.id == member.id:
    #                 async with self.bot.db.session() as session:
    #                     creating_channel: models.Guild.voice_channel_id = await session.scalar(
    #                         select(models.Guild.voice_channel_id)
    #                         .where(models.Guild.guild_id == interaction.guild.id)
    #                     )
    #
    #                 channel2 = self.bot.get_channel(creating_channel)
    #                 await member.move_to(channel2)
    #         await channel.set_permissions(member, connect=False, read_messages=True)
    #         await interaction.response.send_message(
    #             f'拒絕 {member.name} 進入 {interaction.user.mention} 的頻動態語音頻道 ❌')

    @dvc.command()
    async def limit(self, interaction: discord.Interaction, limit: int):
        """設定自己動態語音頻道的最大人數"""
        async with self.bot.db.session() as session:
            voice_id: models.VoiceChannel.voice_id = await session.scalar(
                select(models.VoiceChannel.voice_id)
                .where(models.VoiceChannel.user_id == interaction.user.id)
            )

            if voice_id is None:
                await interaction.response.send_message("請建立一個屬於你的語音頻道")
            else:
                channel = self.bot.get_channel(voice_id)
                await channel.edit(user_limit=limit)
                await interaction.response.send_message("執行完成")

                voice_id: models.UserSettings = await session.scalar(
                    select(models.UserSettings)
                    .where(models.UserSettings.user_id == interaction.user.id)
                )

                if voice_id is None:
                    voice = models.UserSettings(user_id=interaction.user.id, channel_name=f'{interaction.user.name}',
                                                channel_max_people=limit)
                    session.add(voice)
                else:
                    voice_id.channel_max_people = limit
                await session.commit()

    @dvc.command()
    async def rename(self, interaction: discord.Interaction, *, name: str):
        """更改你的動態語音頻道名稱"""
        async with self.bot.db.session() as session:
            voice_id: models.VoiceChannel.voice_id = await session.scalar(
                select(models.VoiceChannel.voice_id)
                .where(models.VoiceChannel.user_id == interaction.user.id)
            )

            if voice_id is None:
                await interaction.response.send_message("請建立一個屬於你的語音頻道")
            else:
                channel = self.bot.get_channel(voice_id)
                await channel.edit(name=name)
                await interaction.response.send_message("執行完成")

                voice: models.UserSettings = await session.scalar(
                    select(models.UserSettings.channel_name)
                    .where(models.UserSettings.user_id == interaction.user.id)
                )

                if voice is None:
                    voice = models.UserSettings(user_id=interaction.user.id, channel_name=name, channel_max_people=0)
                    session.add(voice)
                else:
                    voice.channel_name = name

                await session.commit()
