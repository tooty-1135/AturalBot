from sqlalchemy import Column, Integer, String

from database import Base
from utils.db_type_decorator import DiscordID


class Guild(Base):
    __tablename__ = 'dvc_guild'

    guild_id = Column(DiscordID, primary_key=True)
    voice_channel_id = Column(DiscordID)
    voice_category_id = Column(DiscordID)

    channel_name_template = Column(String(255), default="%s的 頻道")


class UserSettings(Base):
    __tablename__ = 'dvc_user-settings'

    user_id = Column(DiscordID, primary_key=True)
    channel_name = Column(String(255), nullable=True)
    channel_max_people = Column(Integer, default=0)


class VoiceChannel(Base):
    __tablename__ = 'dvc_vc'

    voice_id = Column(DiscordID, nullable=False, primary_key=True)
    user_id = Column(DiscordID, nullable=False)
