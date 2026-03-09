import uuid

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, relationship

from database import Base
from utils.db_type_decorator import DiscordID


class Category(Base):
    __tablename__ = 'ticket_category'

    category_id = Column(DiscordID, nullable=False, primary_key=True)
    guild_id = Column(DiscordID, nullable=False)
    message_id = Column(DiscordID, nullable=False)

    name = Column(String(255), nullable=False)
    # add default user/role permission settings


class Ticket(Base):
    __tablename__ = 'ticket_ticket'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    owner_id = Column(DiscordID, nullable=False)
    channel_id = Column(DiscordID, nullable=False)

    category_id = Column(DiscordID, nullable=False)
