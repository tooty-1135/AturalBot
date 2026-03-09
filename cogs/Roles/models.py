import enum
import uuid

from discord import ButtonStyle
from sqlalchemy import ForeignKey, Integer, String, Column, UniqueConstraint, TypeDecorator, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Layout(Base):
    __tablename__ = "roles_layout"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    guild_id = Column(String(255), nullable=False)

    channel_id = Column(String(255), nullable=True)
    message_id = Column(String(255), unique=True, nullable=True)

    components: Mapped[list["Component"]] = relationship(
        back_populates="layout",
        cascade="all, delete-orphan",
        order_by="Component.position"
    )


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


# Component 的種類
class ComponentType(enum.Enum):
    BUTTON = "button"
    SELECT = "select"
    SELECT_TOGGLE = "select_toggle"


class Component(Base):
    __tablename__ = "roles_component"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    label = Column(String(255), nullable=False)
    type = Column(Enum(ComponentType), nullable=False)
    style = Column(ButtonStyleType, nullable=True)  # for buttons: "primary", "secondary", "success", "danger", "link"

    roles: Mapped[list["Role"]] = relationship(back_populates="component", cascade="all, delete-orphan")

    position = Column(Integer, nullable=False, index=True)  # 控制排序
    linebreak = Column(Boolean, nullable=False, default=False)

    layout_id = Column(String(36), ForeignKey('roles_layout.id', ondelete='CASCADE'), nullable=False)
    layout: Mapped["Layout"] = relationship(back_populates="components")


class Role(Base):
    __tablename__ = "roles_role"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String(255), nullable=False)
    role_id = Column(String(255), nullable=False)
    component_id = Column(String(36), ForeignKey('roles_component.id', ondelete='CASCADE'), nullable=False)
    component: Mapped["Component"] = relationship(back_populates="roles")
