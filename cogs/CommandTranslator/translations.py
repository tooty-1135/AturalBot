from discord import Locale as Lo
from discord.app_commands import TranslationContextLocation as TCL

translations = {
    TCL.command_name: {
        ### all
        "server": {
            Lo.american_english: "guild",
            Lo.taiwan_chinese: "伺服器"
        },
        "user": {
            Lo.american_english: "user",
            Lo.taiwan_chinese: "用戶"
        },
        "setup": {
            Lo.american_english: "setup",
            Lo.taiwan_chinese: "初始化"
        },
        "edit": {
            Lo.american_english: "edit",
            Lo.taiwan_chinese: "編輯"
        },
        "delete": {
            Lo.american_english: "delete",
            Lo.taiwan_chinese: "刪除"
        },
        "layout": {
            Lo.american_english: "layout",
            Lo.taiwan_chinese: "檢視"
        },
        "message": {
            Lo.american_english: "message",
            Lo.taiwan_chinese: "訊息"
        },
        "send": {
            Lo.american_english: "send",
            Lo.taiwan_chinese: "發送"
        },


        ### cmd
        "about_bot": {
            Lo.american_english: "about",
            Lo.taiwan_chinese: "關於"
        },

        ### info ctx menu
        "info_ctx": {
            Lo.american_english: "About User",
            Lo.taiwan_chinese: "關於用戶"
        }
    },
    TCL.command_description: {
        "greets_the_user": {
            Lo.american_english: "Greets the user",
            Lo.taiwan_chinese: "向用戶打招呼"
        },
        "about_this_bot": {
            Lo.american_english: "Provides information about the bot",
            Lo.taiwan_chinese: "提供有關機器人的信息"
        },

        ### info group
        "info_about_server": {
            Lo.american_english: "View information about the current server.",
            Lo.taiwan_chinese: "查看有關當前伺服器的資訊。"
        },
        "info_about_user": {
            Lo.american_english: "View information about a user / member.",
            Lo.taiwan_chinese: "查看有關用戶的資訊。"
        },

        ### roles
        "create_and_manage_role_selection_menus": {
            Lo.american_english: "Create and manage role selection menus.",
            Lo.taiwan_chinese: "建立和管理身份組選單"
        },
        "edit_role_selection_menu": {
            Lo.american_english: "Edit the content of a role selection.",
            Lo.taiwan_chinese: "編輯身份組選單的內容"
        },
        "delete_role_selection_menu_view": {
            Lo.american_english: "Delete a role selection menu view.",
            Lo.taiwan_chinese: "刪除身份組選單檢視"
        },
        "delete_role_selection_menu_message": {
            Lo.american_english: "Delete a role selection menu message.(The view will still be saved in the database.)",
            Lo.taiwan_chinese: "刪除身份組選單訊息(檢視仍會保存在資料庫中。)"
        },
        "send_role_selection_menu": {
            Lo.american_english: "Send a role selection menu to a channel.",
            Lo.taiwan_chinese: "將身份組選單發送到頻道"
        },
    },
    TCL.group_name: {
        "info": {
            Lo.american_english: "info",
            Lo.taiwan_chinese: "關於"
        },
        "roles": {
            Lo.american_english: "roles",
            Lo.taiwan_chinese: "選取身份組"
        },
        "delete": {
            Lo.american_english: "delete",
            Lo.taiwan_chinese: "刪除"
        },
    },
    TCL.group_description: {
        "info_about_sth": {
            Lo.american_english: "Shows information about a user, server, or something else",
            Lo.taiwan_chinese: "顯示用戶、伺服器或其他東西的資訊"
        },
        "role_selection_menus": {
            Lo.american_english: "Create and manage role selection menus",
            Lo.taiwan_chinese: "建立和管理身份組選單"
        },
        "delete_selection_menus": {
            Lo.american_english: "Delete roles menu or message",
            Lo.taiwan_chinese: "刪除身份組選單或訊息"
        },
    },
    TCL.parameter_name: {
    },
    TCL.parameter_description: {
        ### info
        "info_about_user_user": {
            Lo.american_english: "The user to get information about",
            Lo.taiwan_chinese: "要獲取資訊的用戶"
        },

        ### roles
        "id_of_layout": {
            Lo.american_english: "The id of the view.",
            Lo.taiwan_chinese: "檢視的ID。"
        },
        "message_remove": {
            Lo.american_english: "Link or ID of the message to remove.",
            Lo.taiwan_chinese: "要移除的訊息的連結或ID。"
        },
        "channel_send_message": {
            Lo.american_english: "The channel to send the message.",
            Lo.taiwan_chinese: "發送訊息的頻道。"
        },
    },
    # TCL.choice_name: {},
    # TCL.other: {},
    # TCL.strings: {
    #     "info_about_": {
    #         Lo.american_english: "Information about",
    #         Lo.taiwan_chinese: "關於"
    #     },
    #     "Members": {
    #         Lo.american_english: "Members",
    #         Lo.taiwan_chinese: "成員"
    #     },
    #     "_total(people)": {
    #         Lo.american_english: "%s Total",
    #         Lo.taiwan_chinese: "共 %s 人"
    #     },
    #     "Channels": {
    #         Lo.american_english: "Channels",
    #         Lo.taiwan_chinese: "頻道"
    #     },
    #     "Text": {
    #         Lo.american_english: "Text",
    #         Lo.taiwan_chinese: "文字"
    #     },
    #     "Voice": {
    #         Lo.american_english: "Voice",
    #         Lo.taiwan_chinese: "語音"
    #     },
    #     "Total": {
    #         Lo.american_english: "Total",
    #         Lo.taiwan_chinese: "總共"
    #     },
    #     "Installs": {
    #         Lo.american_english: "Installs",
    #         Lo.taiwan_chinese: "安裝統計"
    #     },
    #     "Servers": {
    #         Lo.american_english: "Servers",
    #         Lo.taiwan_chinese: "伺服器"
    #     },
    #     "Users": {
    #         Lo.american_english: "Users",
    #         Lo.taiwan_chinese: "用戶"
    #     },
    #     "Timeline": {
    #         Lo.american_english: "Timeline",
    #         Lo.taiwan_chinese: "時間線"
    #     },
    #     "Created:": {
    #         Lo.american_english: "Created:",
    #         Lo.taiwan_chinese: "建立時間："
    #     },
    #     "Joined server:": {
    #         Lo.american_english: "Joined server:",
    #         Lo.taiwan_chinese: "加入伺服器時間："
    #     },
    #     "Boot time:": {
    #         Lo.american_english: "Boot time:",
    #         Lo.taiwan_chinese: "啟動時間："
    #     },
    #     "cannot_use_in_dm": {
    #         Lo.american_english: "Cannot use this command in private messages.",
    #         Lo.taiwan_chinese: "無法在私人訊息中使用此指令。"
    #     },
    #     "server_created": {
    #         Lo.american_english: "Server created %s.",
    #         Lo.taiwan_chinese: "伺服器建立於 %s。"
    #     },
    #     "members_info": {
    #         Lo.american_english: "Members Info",
    #         Lo.taiwan_chinese: "成員資訊"
    #     },
    #     "roles": {
    #         Lo.american_english: "Roles",
    #         Lo.taiwan_chinese: "身分組"
    #     },
    #     "nitro_level": {
    #         Lo.american_english: "Nitro Level %s",
    #         Lo.taiwan_chinese: "Nitro等級 %s"
    #     },
    #     "nitro_boosters": {
    #         Lo.american_english: "Nitro Boosters",
    #         Lo.taiwan_chinese: "Nitro加成者"
    #     },
    #     "nitro_boosts": {
    #         Lo.american_english: "Nitro Boosts",
    #         Lo.taiwan_chinese: "Nitro加成數"
    #     },
    #     "stage": {
    #         Lo.american_english: "Stage",
    #         Lo.taiwan_chinese: "舞台"
    #     },
    #     "user_information": {
    #         Lo.american_english: "User Information",
    #         Lo.taiwan_chinese: "用戶資訊"
    #     },
    #     "created": {
    #         Lo.american_english: "Created",
    #         Lo.taiwan_chinese: "建立時間"
    #     },
    #     "profile": {
    #         Lo.american_english: "Profile",
    #         Lo.taiwan_chinese: "個人資料"
    #     },
    #     "member_information": {
    #         Lo.american_english: "Member Information",
    #         Lo.taiwan_chinese: "成員資訊"
    #     },
    #     "joined": {
    #         Lo.american_english: "Joined",
    #         Lo.taiwan_chinese: "加入時間"
    #     },
    #     "unknown": {
    #         Lo.american_english: "Unknown",
    #         Lo.taiwan_chinese: "未知"
    #     },
    #     "made_with": {
    #         Lo.american_english: "Made with discord.py v%s by %s",
    #         Lo.taiwan_chinese: "使用 discord.py v%s 由 %s 製作"
    #     }
    # }
}
