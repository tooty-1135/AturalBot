import logging

import discord
from discord import ButtonStyle, Color, SelectOption
from discord.ui import Button, Select, View, RoleSelect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from utils.views import interaction_defer
from . import models
from .models import Component, ComponentType as RolesComponentType

from translator import Translator
from .translations import translations

LOGGER = logging.getLogger(__name__)
_ = Translator(translations).translate


# class RolesCreateSelect(Select):
#     """Select menu to select which roles will be available to select in the message."""
#
#     def __init__(self, roles: list[discord.Role]):
#         options = [discord.SelectOption(label=role.name, value=str(role.id)) for role in roles]  # label會被當成value
#         self._roles = roles
#         self.view: RolesCreateView
#         super().__init__(
#             placeholder="Select roles from the available list.",
#             options=options,
#             max_values=len(options),
#         )
#
#     async def callback(self, interaction: discord.Interaction):
#         selected_roles = [
#             discord.utils.get(self._roles, id=int(value)) for value in self.values
#         ]
#         self.view.selected_roles = sorted(
#             [r for r in selected_roles if r is not None],
#             reverse=True,
#         )
#         await interaction.response.defer()
#         self.view.stop()


def get_ordered_components(components: list[Component]) -> list[list[Component]]:
    """把一維結構的components轉成二維"""
    # component要依照順序排列
    result: list[list[Component]] = []
    current_row: list[Component] = []

    for comp in components:
        current_row.append(comp)

        if comp.linebreak:
            if current_row:  # 有東西才換行
                result.append(current_row)
                current_row = []
            continue

        if len(current_row) >= 5:  # 每行最多5個component，剩下換行(避免沒搞到linebreak)
            result.append(current_row)
            current_row = []

    if current_row:  # 不知道有沒有用，反正放一下
        logging.debug("Appending remaining components to result")
        result.append(current_row)

    return result


def get_components_list(components: list[list[Component]]) -> list[Component]:
    """把二維結構的components轉成一維，並且補上linebreak"""
    result: list[Component] = []

    position = 0

    for row in components:
        for idx, comp in enumerate(row):
            if idx == len(row) - 1:
                comp.linebreak = True
            else:
                comp.linebreak = False

            comp.position = position

            result.append(comp)

            position += 1

    return result


async def sync_components(session: AsyncSession, layout_id: str, new_components: list[Component]):
    """
    同步 DB 中的 components 和 roles (async 版本)
    """
    # 重新查一次，確保 relationships 已經被 eager load
    result = await session.execute(
        select(models.Layout)
        .where(models.Layout.id == layout_id)
        .options(
            selectinload(models.Layout.components).selectinload(models.Component.roles)
        )
    )
    layout = result.scalar_one()

    existing_components = {c.id: c for c in layout.components if c.id is not None}
    seen_component_ids = set()

    for comp in new_components:
        if comp.id and comp.id in existing_components:
            # 更新已存在的 component
            db_comp = existing_components[comp.id]
            db_comp.type = comp.type
            db_comp.label = comp.label
            db_comp.style = comp.style
            db_comp.position = comp.position
            db_comp.linebreak = comp.linebreak
            seen_component_ids.add(comp.id)

            # --- 同步 roles ---
            existing_roles = {r.id: r for r in db_comp.roles if r.id is not None}
            seen_role_ids = set()

            for role in comp.roles:
                if role.id and role.id in existing_roles:
                    db_role = existing_roles[role.id]
                    db_role.label = role.label
                    db_role.role_id = role.role_id
                    seen_role_ids.add(role.id)
                else:
                    role.component = db_comp
                    session.add(role)

            for role_id, db_role in existing_roles.items():
                if role_id not in seen_role_ids:
                    await session.delete(db_role)

        else:
            # 新增 component
            comp.layout = layout
            session.add(comp)

    # 刪除多餘的 components
    for comp_id, db_comp in existing_components.items():
        if comp_id not in seen_component_ids:
            await session.delete(db_comp)

    await session.commit()


# 其實可以不用exclude_select，之後看情況移除
def available_rows(components, min_comps: int, exclude_select: bool = False):
    rows = len(components)

    positions = []
    for i in range(0, rows):
        if len(components[i]) < min_comps:
            if exclude_select:
                if any(c.type in [RolesComponentType.SELECT, RolesComponentType.SELECT_TOGGLE] for c in components[i]):
                    continue
            positions.append(i)

    return positions


class RolesEditorBase(View):
    """View sent to create a roles selection menu for members."""

    def __init__(self, author: discord.Member, cog, components, layout_id: str = None, locale: discord.Locale = None):
        super().__init__()
        self.author = author
        self.layout_id = layout_id
        self.cog = cog
        self.components = components
        self.locale = locale

    async def interaction_check(self, interaction: discord.Interaction):
        """Only the command author can use the View."""

        return interaction.user == self.author


class RolesEditor_AddComp_Type(RolesEditorBase):
    def __init__(self, old_class):
        super().__init__(author=old_class.author, components=old_class.components, layout_id=old_class.layout_id,
                         cog=old_class.cog, locale=old_class.locale)

        self.comp_type_select = Select(
            placeholder=_('roles_select_type', self.locale),
            options=[
                SelectOption(label=_('roles_select_type_button', self.locale), value=RolesComponentType.BUTTON.value),
                SelectOption(label=_('roles_select_type_select', self.locale), value=RolesComponentType.SELECT.value),
                SelectOption(label=_('roles_select_type_toggle', self.locale),
                             value=RolesComponentType.SELECT_TOGGLE.value)
            ],
            row=0
        )
        self.comp_type_select.callback = self.select_callback
        self.add_item(self.comp_type_select)

        self.back_button = Button(label=_('roles_back', self.locale), style=ButtonStyle.red, row=1)
        self.back_button.callback = self.back_callback
        self.add_item(self.back_button)

    async def select_callback(self, interaction: discord.Interaction):
        selected = self.comp_type_select.values[0]
        await interaction.response.edit_message(content=f"Selected component type: {selected}",
                                                view=RolesEditor_AddComp(old_class=self,
                                                                         comp_type=RolesComponentType(selected)))
        self.stop()

    async def back_callback(self, interaction: discord.Interaction):
        new_view = RolesView_Preview(old_class=self)
        await interaction.response.edit_message(content=_('roles_preview_mode', self.locale), view=new_view)
        self.stop()


class RolesEditor_AddComp(RolesEditorBase):
    def __init__(self, old_class, comp_type: RolesComponentType):
        super().__init__(author=old_class.author, components=old_class.components, layout_id=old_class.layout_id,
                         cog=old_class.cog, locale=old_class.locale)

        self.comp_type = comp_type

        rows = len(self.components)

        if rows < 4:
            self.components.append([])

        if comp_type.value.startswith("select"):
            role_select = RoleSelect(placeholder=_('roles_select_roles', self.locale), max_values=24, row=0)

            aval_rows = available_rows(self.components, 1)
            if len(aval_rows) == 0:
                position_select = discord.ui.Select(
                    placeholder=_('roles_no_row', self.locale),
                    options=[SelectOption(label=_('roles_no_row', self.locale))],
                    row=1,
                    max_values=1,
                    disabled=True
                )
            else:
                position_select = discord.ui.Select(
                    placeholder=_('roles_select_position', self.locale),
                    options=[SelectOption(label=_('roles_row', self.locale).format(i + 1), value=str(i)) for i in
                             aval_rows],
                    row=1,
                    max_values=1
                )
        else:
            role_select = discord.ui.RoleSelect(placeholder=_('roles_select_role', self.locale), max_values=1, row=0)

            aval_rows = available_rows(self.components, 5, exclude_select=True)
            if len(aval_rows) == 0:
                position_select = discord.ui.Select(
                    placeholder=_('roles_no_row', self.locale),
                    options=[SelectOption(label=_('roles_no_row', self.locale))],
                    row=1,
                    max_values=1,
                    disabled=True
                )
            else:
                position_select = discord.ui.Select(
                    placeholder=_('roles_select_position', self.locale),
                    options=[SelectOption(label=_('roles_row', self.locale).format(i + 1), value=str(i)) for i in
                             aval_rows],
                    row=1,
                    max_values=1
                )

        self.role_select = role_select
        role_select.callback = interaction_defer
        self.add_item(role_select)

        self.position_select = position_select
        position_select.callback = interaction_defer
        self.add_item(position_select)

        self.confirm_button = Button(label=_('roles_confirm', self.locale), style=ButtonStyle.green, row=2)
        self.confirm_button.callback = self.confirm
        self.add_item(self.confirm_button)

        self.back_button = Button(label=_('roles_back', self.locale), style=ButtonStyle.red, row=2)
        self.back_button.callback = self.back_callback
        self.add_item(self.back_button)

    async def confirm(self, interaction: discord.Interaction):
        if len(self.role_select.values) == 0 or len(self.position_select.values) == 0:
            await interaction.response.send_message(_('roles_select_one', self.locale),
                                                    ephemeral=True)
            return

        match self.comp_type:
            case RolesComponentType.BUTTON:
                comp_label = self.role_select.values[0].name
            case RolesComponentType.SELECT:
                comp_label = _('roles_select_roles', self.locale)
            case RolesComponentType.SELECT_TOGGLE:
                comp_label = _('roles_select_role', self.locale)
            case _:
                comp_label = "Add role"

        self.components[int(self.position_select.values[0])].append(
            Component(
                type=self.comp_type,
                label=comp_label,
                style=ButtonStyle.gray if self.comp_type.value.startswith("button") else None,
                roles=[models.Role(role_id=str(r.id), label=r.name) for r in self.role_select.values],
            )
        )

        new_view = RolesView_Preview(old_class=self)
        await interaction.response.edit_message(content=_('roles_preview_mode', self.locale), view=new_view)

        self.stop()

    async def back_callback(self, interaction: discord.Interaction):
        if not self.components[-1]:
            del self.components[-1]

        new_view = RolesView_Preview(old_class=self)
        await interaction.response.edit_message(content=_('roles_preview_mode', self.locale), view=new_view)
        self.stop()


class EditComp_Modal(discord.ui.Modal, title="Edit Component"):
    new_label: str

    def __init__(self, current_label: str, locale: discord.Locale):
        super().__init__()

        self.label_input = discord.ui.TextInput(label='label', style=discord.TextStyle.short, default=current_label)
        self.add_item(self.label_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.new_label = self.label_input.value
        await interaction.response.defer()


class RolesEditor_EditComp(RolesEditorBase):
    def __init__(self, old_class, row: int, index: int):
        super().__init__(author=old_class.author, components=old_class.components, layout_id=old_class.layout_id,
                         cog=old_class.cog, locale=old_class.locale)
        self.row = row
        self.index = index
        self.component = self.components[row][index]

        comp = self.component
        if comp.type.value.startswith("select"):
            select = Select(
                placeholder=comp.label,
                options=[SelectOption(label="testtest", value="testtest")],
                disabled=True,
                row=0
            )
            self.add_item(select)
        elif comp.type.value.startswith("button"):
            button = Button(
                label=comp.label,
                style=comp.style,
                disabled=True,
                row=0
            )
            self.add_item(button)

            edit_style_button = Button(label=_('roles_edit_style', self.locale), style=ButtonStyle.blurple, row=1)
            edit_style_button.callback = self.edit_style
            self.add_item(edit_style_button)

        edit_text_button = Button(label=_('roles_edit_text', self.locale), style=ButtonStyle.blurple, row=1)
        edit_text_button.callback = self.edit_label
        self.add_item(edit_text_button)

        self.add_item(
            Button(label=_('roles_move_component', self.locale), style=ButtonStyle.link, url="https://example.com",
                   row=1))

        del_comp_button = Button(label=_('roles_delete_component', self.locale), style=ButtonStyle.red, row=1)
        del_comp_button.callback = self.delete_component
        self.add_item(del_comp_button)

        back_button = Button(label=_('roles_back', self.locale), style=ButtonStyle.red, row=2)
        back_button.callback = self.back_callback
        self.add_item(back_button)

    async def edit_label(self, interaction: discord.Interaction):
        modal = EditComp_Modal(current_label=self.component.label, locale=self.locale)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if hasattr(modal, 'new_label'):
            self.component.label = modal.new_label

            await interaction.message.edit(content=_('roles_editing_component', self.locale),
                                           view=RolesEditor_EditComp(old_class=self, row=self.row,
                                                                     index=self.index))

    async def edit_style(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=RolesEditor_EditCompStyle(old_class=self, row=self.row,
                                                                               index=self.index))

    async def delete_component(self, interaction: discord.Interaction):
        logging.debug(f"total {len(self.components[self.row])} components in row {self.row}")
        if len(self.components[self.row]) == 1:  # 如果只有一個component
            del self.components[self.row]
        else:
            del self.components[self.row][self.index]

        new_view = RolesView_Preview(old_class=self)
        await interaction.response.edit_message(content=_('roles_preview_mode', self.locale), view=new_view)

    async def back_callback(self, interaction: discord.Interaction):
        new_view = RolesView_Preview(old_class=self)
        await interaction.response.edit_message(content=_('roles_preview_mode', self.locale), view=new_view)
        self.stop()


class RolesEditor_EditCompStyle(RolesEditorBase):
    def __init__(self, old_class, row: int, index: int):
        super().__init__(author=old_class.author, components=old_class.components, layout_id=old_class.layout_id,
                         cog=old_class.cog, locale=old_class.locale)
        self.row = row
        self.index = index
        self.component = self.components[row][index]

        comp = self.component
        if comp.type.value.startswith("select"):
            select = Select(
                placeholder=comp.label,
                disabled=True,
                row=0
            )
            self.add_item(select)
        elif comp.type.value.startswith("button"):
            button = Button(
                label=comp.label,
                style=comp.style,
                disabled=True,
                row=0
            )
            self.add_item(button)

        self.style_select = Select(
            placeholder=_('roles_select_style', self.locale),
            row=1,
            options=[
                SelectOption(label=_('roles_style_green', self.locale), value=str(ButtonStyle.green.value)),
                SelectOption(label=_('roles_style_blurple', self.locale), value=str(ButtonStyle.blurple.value)),
                SelectOption(label=_('roles_style_red', self.locale), value=str(ButtonStyle.red.value)),
                SelectOption(label=_('roles_style_gray', self.locale), value=str(ButtonStyle.gray.value))
            ]
        )
        self.style_select.callback = self.select_style
        self.add_item(self.style_select)

        back_button = Button(label=_('roles_back', self.locale), style=ButtonStyle.red, row=2)
        back_button.callback = self.back_callback
        self.add_item(back_button)

    async def select_style(self, interaction: discord.Interaction):
        selected = int(self.style_select.values[0])
        self.component.style = ButtonStyle(selected)

        await interaction.response.edit_message(view=RolesEditor_EditComp(old_class=self, row=self.row,
                                                                          index=self.index))

    async def back_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=RolesEditor_EditComp(old_class=self, row=self.row,
                                                                          index=self.index))
        self.stop()


class RolesSelect(Select):
    """Select menu with the list of assignable roles."""

    def __init__(self, roles: list[models.Role], label: str, custom_id: str, row: int, max_values: int = None):
        # roles = sorted(roles, reverse=True)
        roles = roles
        options = [discord.SelectOption(label=role.label, value=str(role.role_id)) for role in roles]
        # TODO: 使用伺服器的主要語言
        options.append(discord.SelectOption(label=_('roles_clear', None), value="clear"))

        print(options)

        self.roles = roles

        self.label = label
        super().__init__(
            placeholder=self.label,
            options=options,
            max_values=max_values or len(options),
            custom_id=custom_id,
            row=row,
        )

    async def clear_roles(self, interaction: discord.Interaction):
        """Clear all roles.
        if custom_id.include('clear'): send_modal(clear_confirm)"""

    async def callback(self, interaction: discord.Interaction):
        """Edit the roles of the member, removing unselected roles
        and adding the selected ones
        """
        roles = [discord.utils.get(interaction.guild.roles, id=int(role.role_id)) for role in self.roles]

        member = interaction.user
        assert isinstance(member, discord.Member)

        selected_roles = [
            discord.utils.get(roles, id=int(value)) for value in self.values
        ]
        selected_roles = [r for r in selected_roles if r is not None]

        added_roles = [role for role in selected_roles if role not in member.roles]

        removed_roles = [
            roles
            for role in self.roles
            if (role in member.roles) and (role not in selected_roles)
        ]

        if removed_roles:
            LOGGER.debug(
                f"Removing roles {', '.join([str(r) for r in removed_roles])} "
                f"to {member}"
            )
            await member.remove_roles(*removed_roles)

        if added_roles:
            added_roles_str = ", ".join([r.name for r in added_roles])
            LOGGER.debug(f"Adding roles {added_roles_str} to {member}")
            await member.add_roles(*added_roles)

        await interaction.response.send_message(
            embed=discord.Embed(
                title=_('roles_set_roles', interaction.locale).format(', '.join(r.name for r in selected_roles)),
                color=Color.green(),
            ),
            ephemeral=True,
        )


class RolesViewBase(View):
    """Base View class for role selection UI."""

    def __init__(
            self, components: list[list[Component]], locale: discord.Locale = None
    ):
        super().__init__(timeout=None)
        self.locale = locale

        if components == []:
            button = Button(
                label=_('roles_no_components', self.locale),
                style=ButtonStyle.gray,
                row=0,
                disabled=True,
            )
            self.add_item(button)

        self.components = components

        logging.debug(self.components)

        for row, comps in enumerate(components):
            for pos, comp in enumerate(comps):
                if comp.type == RolesComponentType.SELECT:
                    select = RolesSelect(
                        label=comp.label,
                        roles=[r for r in comp.roles],
                        custom_id=f"{row}, {pos}",
                        row=row
                    )
                    select.callback = self.select_callback
                    self.add_item(select)
                if comp.type == RolesComponentType.SELECT_TOGGLE:
                    select = RolesSelect(
                        label=comp.label,
                        roles=[r for r in comp.roles],
                        custom_id=f"{row}, {pos}",
                        row=row,
                        max_values=1
                    )
                    select.callback = self.select_callback
                    self.add_item(select)
                elif comp.type == RolesComponentType.BUTTON:
                    button = Button(
                        label=comp.label,
                        style=comp.style,
                        custom_id=f"{row}, {pos}, {comp.roles[0].role_id}",
                        row=row,
                    )
                    button.callback = self.button_callback
                    self.add_item(button)

    async def select_callback(self, interaction: discord.Interaction):
        """Override this method in subclasses"""
        pass

    async def button_callback(self, interaction: discord.Interaction):
        """Override this method in subclasses"""
        pass


class RolesView_Preview(RolesViewBase):
    """Preview version of the roles view with non-functional callbacks."""

    def __init__(self, old_class):
        super().__init__(components=old_class.components, locale=old_class.locale)
        self.author = old_class.author
        self.layout_id = old_class.layout_id
        self.cog = old_class.cog

        save_button = Button(label=_('roles_save', self.locale), style=ButtonStyle.green, row=4)
        save_button.callback = self.save_callback
        self.add_item(save_button)

        cancel_button = Button(label=_('roles_cancel', self.locale), style=ButtonStyle.red, row=4)
        cancel_button.callback = self.cancel_callback
        self.add_item(cancel_button)

        add_button = Button(label=_('roles_add_component', self.locale), style=ButtonStyle.blurple, row=4)
        add_button.callback = self.add_callback
        self.add_item(add_button)

        self.add_item(
            Button(label=_('roles_dashboard', self.locale), style=ButtonStyle.link, url="https://example.com", row=4))

    async def save_callback(self, interaction: discord.Interaction):
        if self.layout_id:
            async with self.cog.bot.db.session() as session:
                view_model: models.Layout = await session.scalar(
                    select(models.Layout)
                    .where(models.Layout.id == self.layout_id)
                    .options(
                        joinedload(models.Layout.components).joinedload(models.Component.roles))
                )

                assert view_model is not None

                new_components = get_components_list(self.components)
                await sync_components(session, view_model.id, new_components)

                if view_model.channel_id and view_model.message_id:
                    channel: discord.TextChannel = await self.cog.bot.fetch_channel(int(view_model.channel_id))
                    message = await channel.fetch_message(int(view_model.message_id))
                    assert message is not None

                    new_view = RolesView_Normal(components=self.components, locale=interaction.guild.preferred_locale)
                    await message.edit(view=new_view)

                await interaction.response.edit_message(content=_('roles_changes_saved', self.locale), view=None)
                self.stop()
        else:
            async with self.cog.bot.db.session() as session:
                view_model = models.Layout(
                    guild_id=str(interaction.guild_id)
                )
                session.add(view_model)
                await session.commit()

                new_components = get_components_list(self.components)
                await sync_components(session, view_model.id, new_components)

                await interaction.response.edit_message(
                    content=_('roles_layout_created', self.locale).format(view_model.id),
                    view=None)
                self.stop()

    async def cancel_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=_('roles_editing_cancelled', self.locale), view=None)
        self.stop()

    async def add_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=_('roles_select_type_add', self.locale),
            view=RolesEditor_AddComp_Type(old_class=self))

    async def button_callback(self, interaction: discord.Interaction):
        row, index, rid = map(int, interaction.data['custom_id'].split(", "))

        await interaction.response.edit_message(
            content=_('roles_editing_component', self.locale),
            view=RolesEditor_EditComp(old_class=self, row=int(row), index=int(index)))

    async def select_callback(self, interaction: discord.Interaction):
        row, index = map(int, interaction.data['custom_id'].split(", "))

        await interaction.response.edit_message(
            content=_('roles_editing_component', self.locale),
            view=RolesEditor_EditComp(old_class=self, row=int(row), index=int(index)))

    async def interaction_check(self, interaction: discord.Interaction):
        """Only the command author can use the View."""

        return interaction.user == self.author


class RolesView_Normal(RolesViewBase):
    """Normal version of the roles view with working callbacks."""

    # TODO: 考慮將roles的選單獨立出來，照著原本的寫法
    async def select_callback(self, interaction: discord.Interaction):
        logging.debug(interaction.data)
        row, index = map(int, interaction.data['custom_id'].split(", "))

        _selected_roles_id = interaction.data['values']

        if "clear" in _selected_roles_id:
            _selected_roles_id = []

        member = interaction.user
        assert isinstance(member, discord.Member)
        select_options = self.components[row][index].roles

        selected_roles = []
        for value in _selected_roles_id:
            comp = discord.utils.get(select_options, role_id=value)
            if comp is not None:
                selected_roles.append(comp.role_id)

        member_roles = [str(role.id) for role in member.roles]

        added_roles = []
        for role in selected_roles:
            if role not in member_roles:
                role = discord.utils.get(interaction.guild.roles, id=int(role))
                if role is not None:
                    added_roles.append(role)

        removed_roles = []
        for role in select_options:
            if str(role.role_id) in member_roles and str(role.role_id) not in selected_roles:
                role = discord.utils.get(interaction.guild.roles, id=int(role.role_id))
                if role is not None:
                    removed_roles.append(role)

        if removed_roles:
            LOGGER.debug(
                f"Removing roles {', '.join([str(r) for r in removed_roles])} "
                f"to {member}"
            )
            await member.remove_roles(*removed_roles)

        if added_roles:
            added_roles_str = ", ".join([r.name for r in added_roles])
            LOGGER.debug(f"Adding roles {added_roles_str} to {member}")
            await member.add_roles(*added_roles)

        await interaction.response.defer()

    async def button_callback(self, interaction: discord.Interaction):
        logging.debug(interaction.data)
        row, index, role_id = map(int, interaction.data['custom_id'].split(", "))

        member = interaction.user
        assert isinstance(member, discord.Member)

        member_roles = member.roles
        role = discord.utils.get(interaction.guild.roles, id=int(role_id))
        if role is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Cannot find the role.",
                    color=Color.red(),
                ),
                ephemeral=True,
            )
            return

        if role in member_roles:
            LOGGER.debug(f"Removing role {role} to {member}")
            await member.remove_roles(role)
        else:
            LOGGER.debug(f"Adding role {role} to {member}")
            await member.add_roles(role)
        await interaction.response.defer()


class SelectLayoutView(View):
    selected_layout: models.Layout | None = None

    def __init__(self, views: list[models.Layout]) -> None:
        super().__init__(timeout=None)

        self.views = views

        options = [SelectOption(label=f"{idx + 1}. {view.id}", value=str(idx)) for idx, view in
                   enumerate(views)]
        # TODO: 使用伺服器的主要語言
        self.select = Select(placeholder=_('roles_select_layout', None), options=options, max_values=1, row=0)
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        selected_layout_order = int(self.select.values[0])
        selected_layout = self.views[selected_layout_order]
        self.selected_layout = selected_layout

        if selected_layout is None:
            logging.debug(f"View {self.select.values[0]} not found.")

        await interaction.response.defer()
        self.stop()
