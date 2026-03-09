import discord
from discord import ButtonStyle, Message
from sqlalchemy import TypeDecorator, Integer, VARCHAR

import utils.type


class ButtonStyleType(TypeDecorator):
    """在 DB 裡存 int，Python 端用 discord.ButtonStyle"""
    impl = Integer
    cache_ok = True  # 告訴 SQLAlchemy 這個 TypeDecorator 可以被快取

    def process_bind_param(self, value, dialect):
        """寫入 DB 前的轉換"""
        if value is None:
            return None
        if isinstance(value, ButtonStyle):
            return value.value
        return int(value)  # 如果給 int 也能接受

    def process_result_value(self, value, dialect):
        """從 DB 讀取後的轉換"""
        if value is None:
            return None
        return ButtonStyle(value)


class DiscordID(TypeDecorator):
    impl = VARCHAR(255)
    cache_ok = True  # 告訴 SQLAlchemy 這個 TypeDecorator 可以被快取

    def process_bind_param(self, value, dialect) -> str | None:
        """寫入 DB 前的轉換"""
        if not value:
            return None
        return str(value)

    def process_result_value(self, value, dialect) -> int | None:
        """從 DB 讀取後的轉換"""
        if not value:
            return None
        return int(value)


class DiscordMessage(TypeDecorator):
    impl = VARCHAR(255)
    cache_ok = True  # 告訴 SQLAlchemy 這個 TypeDecorator 可以被快取

    def process_bind_param(self, value, dialect) -> str | None:
        """寫入 DB 前的轉換"""
        if not value:
            return None

        if hasattr(value, "channel_id"):
            channel_id = value.channel_id
        else:
            channel_id = value.channel.id

        return f"{channel_id},{value.id}"

    def process_result_value(self, value, dialect) -> utils.type.PartialMessage | None:
        """從 DB 讀取後的轉換"""
        if not value:
            return None

        ch_id, msg_id = value.split(",")

        # 現在我們得取得channel來組成一個完整的message
        # message沒有channel_id，只有channel.id
        message = utils.type.PartialMessage(ch_id, msg_id)

        return message
