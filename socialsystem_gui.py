"""
socialsystem_gui.py
===================
Tkinter 社交系统全功能白盒 GUI（中文版）
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from typing import Dict, List, Tuple

from socialsystem import MentorshipSystem, SocialSystem


class SocialSystemGUI:
    def __init__(self) -> None:
        self.system = SocialSystem()

        self.root = tk.Tk()
        self.root.title("武侠 MMO 社交系统白盒 GUI")
        self.root.geometry("1460x840")
        self.root.minsize(1240, 720)

        self._setup_style()
        self._build_layout()

        self.modules = self._build_modules()
        self.current_module_key = ""
        self.current_operation_key = ""

        self.switch_module("player")

    def _setup_style(self) -> None:
        self.root.configure(bg="#f4f4f4")
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # 中文字体回退策略，避免显示成 ???
        candidate_fonts = [
            "Microsoft YaHei",
            "SimHei",
            "SimSun",
            "Noto Sans CJK SC",
            "PingFang SC",
            "Arial Unicode MS",
            "Segoe UI",
        ]
        available = set(tkfont.families(self.root))
        chosen = None
        for f in candidate_fonts:
            if f in available:
                chosen = f
                break
        if chosen is None:
            chosen = "TkDefaultFont"

        self.ui_font = (chosen, 10)
        self.ui_font_header = (chosen, 12, "bold")
        self.log_font = (chosen, 10)

        self.style.configure("TFrame", background="#f4f4f4")
        self.style.configure("Card.TFrame", background="#ffffff")
        self.style.configure("TLabel", background="#f4f4f4", foreground="#202020", font=self.ui_font)
        self.style.configure("Header.TLabel", font=self.ui_font_header)
        self.style.configure("Hint.TLabel", foreground="#666666")
        self.style.configure("Menu.TButton", anchor="w", padding=(10, 7), font=self.ui_font)
        self.style.configure("TButton", padding=(8, 5), font=self.ui_font)

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=0, minsize=230)
        self.root.columnconfigure(1, weight=1, minsize=640)
        self.root.columnconfigure(2, weight=1, minsize=520)
        self.root.rowconfigure(0, weight=1)

        self.left_panel = ttk.Frame(self.root, style="Card.TFrame", padding=12)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 7), pady=10)

        self.center_panel = ttk.Frame(self.root, style="Card.TFrame", padding=14)
        self.center_panel.grid(row=0, column=1, sticky="nsew", padx=7, pady=10)

        self.right_panel = ttk.Frame(self.root, style="Card.TFrame", padding=10)
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=(7, 10), pady=10)

        self._build_left_menu()
        self._build_center_area()
        self._build_log_area()

    def _build_left_menu(self) -> None:
        ttk.Label(self.left_panel, text="主菜单", style="Header.TLabel").pack(anchor="w", pady=(2, 10))

        menus = [
            ("玩家管理", "player"),
            ("好友系统", "friend"),
            ("师徒系统", "mentor"),
            ("结义系统", "jieyi"),
            ("结缘系统", "romance"),
            ("帮派系统", "guild"),
            ("系统时间", "system"),
        ]
        for text, key in menus:
            ttk.Button(self.left_panel, text=text, style="Menu.TButton", command=lambda k=key: self.switch_module(k)).pack(fill="x", pady=3)

        ttk.Separator(self.left_panel).pack(fill="x", pady=10)
        ttk.Button(self.left_panel, text="初始化演示数据", command=self.init_demo_data).pack(fill="x", pady=3)
        ttk.Button(self.left_panel, text="查看全部玩家", command=lambda: self._log_lines(self.system.list_players())).pack(fill="x", pady=3)

    def _build_center_area(self) -> None:
        self.center_panel.columnconfigure(0, weight=1)
        self.center_panel.rowconfigure(4, weight=1)

        self.module_title = ttk.Label(self.center_panel, text="", style="Header.TLabel")
        self.module_title.grid(row=0, column=0, sticky="w")

        self.day_label = ttk.Label(self.center_panel, text="", style="Hint.TLabel")
        self.day_label.grid(row=1, column=0, sticky="w", pady=(4, 10))

        op_row = ttk.Frame(self.center_panel, style="Card.TFrame")
        op_row.grid(row=2, column=0, sticky="ew")
        op_row.columnconfigure(1, weight=1)

        ttk.Label(op_row, text="当前操作：").grid(row=0, column=0, sticky="w")
        self.operation_combo = ttk.Combobox(op_row, state="readonly")
        self.operation_combo.grid(row=0, column=1, sticky="ew")
        self.operation_combo.bind("<<ComboboxSelected>>", self._on_operation_changed)

        self.operation_hint = ttk.Label(self.center_panel, text="", style="Hint.TLabel")
        self.operation_hint.grid(row=3, column=0, sticky="w", pady=(8, 8))

        self.form_frame = ttk.Frame(self.center_panel, style="Card.TFrame")
        self.form_frame.grid(row=4, column=0, sticky="nsew")
        self.form_frame.columnconfigure(1, weight=1)

        action_row = ttk.Frame(self.center_panel, style="Card.TFrame")
        action_row.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        action_row.columnconfigure((0, 1, 2), weight=1)

        ttk.Button(action_row, text="执行", command=self.run_current_operation).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(action_row, text="清空", command=self.clear_inputs).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(action_row, text="退出", command=self.root.destroy).grid(row=0, column=2, sticky="ew", padx=(6, 0))

        self.entry_widgets: Dict[str, tk.Widget] = {}

    def _build_log_area(self) -> None:
        ttk.Label(self.right_panel, text="状态日志", style="Header.TLabel").pack(anchor="w")
        ttk.Label(self.right_panel, text="所有方法调用结果都会追加到这里。", style="Hint.TLabel").pack(anchor="w", pady=(4, 8))

        self.log_text = tk.Text(
            self.right_panel,
            wrap="word",
            bg="#fafafa",
            fg="#222222",
            font=self.log_font,
            relief="solid",
            borderwidth=1,
            state="disabled",
        )
        self.log_text.pack(fill="both", expand=True)

    def _build_modules(self) -> Dict[str, Dict]:
        return {
            "player": {
                "title": "玩家管理",
                "operations": {
                    "create_player": {"label": "创建玩家", "hint": "SocialSystem.create_player", "fields": [("player_id", "玩家ID", "int", ""), ("nickname", "昵称", "text", ""), ("level", "等级", "int", "1")], "handler": self.op_create_player},
                    "list_players": {"label": "查看玩家列表", "hint": "SocialSystem.list_players", "fields": [], "handler": self.op_list_players},
                    "set_online": {"label": "设置在线状态", "hint": "SocialSystem.set_online", "fields": [("player_id", "玩家ID", "int", ""), ("online", "在线(y/n)", "bool", "y")], "handler": self.op_set_online},
                    "set_level": {"label": "设置玩家等级", "hint": "SocialSystem.set_level", "fields": [("player_id", "玩家ID", "int", ""), ("new_level", "新等级", "int", "")], "handler": self.op_set_level},
                },
            },
            "friend": {
                "title": "好友系统",
                "operations": {
                    "send_request": {"label": "发起好友申请", "hint": "FriendSystem.send_request", "fields": [("from_id", "申请方ID", "int", ""), ("to_id", "被申请方ID", "int", "")], "handler": self.op_friend_send_request},
                    "respond_request": {"label": "处理好友申请", "hint": "FriendSystem.respond_request", "fields": [("target_id", "处理方ID", "int", ""), ("requester_id", "申请方ID", "int", ""), ("accept", "同意(y/n)", "bool", "y")], "handler": self.op_friend_respond},
                    "increase_intimacy": {"label": "增加亲密度", "hint": "FriendSystem.increase_intimacy", "fields": [("a_id", "玩家A", "int", ""), ("b_id", "玩家B", "int", ""), ("action", "行为", "text", "组队"), ("amount", "自定义增量(可空)", "text", ""), ("reason", "自定义原因(可空)", "text", "")], "handler": self.op_friend_increase_intimacy},
                    "view_friend_list": {"label": "查看好友列表", "hint": "FriendSystem.view_friend_list", "fields": [("player_id", "玩家ID", "int", "")], "handler": self.op_friend_view_list},
                    "remove_friend": {"label": "删除好友", "hint": "FriendSystem.remove_friend", "fields": [("a_id", "玩家A", "int", ""), ("b_id", "玩家B", "int", "")], "handler": self.op_friend_remove},
                    "reserve_block_interface": {"label": "预留拉黑接口", "hint": "FriendSystem.reserve_block_interface", "fields": [("player_id", "玩家ID", "int", ""), ("target_id", "目标ID", "int", "")], "handler": self.op_friend_block_interface},
                },
            },
            "mentor": {
                "title": "师徒系统",
                "operations": {
                    "bind": {"label": "建立师徒关系", "hint": "MentorshipSystem.bind", "fields": [("master_id", "师父ID", "int", ""), ("apprentice_id", "徒弟ID", "int", "")], "handler": self.op_mentor_bind},
                    "daily_task": {"label": "完成每日师徒任务", "hint": "MentorshipSystem.complete_daily_task", "fields": [("master_id", "师父ID", "int", ""), ("apprentice_id", "徒弟ID", "int", ""), ("teamed", "组队(y/n)", "bool", "y")], "handler": self.op_mentor_daily},
                    "weekly_task": {"label": "完成周常师徒任务", "hint": "MentorshipSystem.complete_weekly_task", "fields": [("master_id", "师父ID", "int", ""), ("apprentice_id", "徒弟ID", "int", ""), ("teamed", "组队(y/n)", "bool", "y")], "handler": self.op_mentor_weekly},
                    "dissolve": {"label": "解除师徒关系", "hint": "MentorshipSystem.dissolve", "fields": [("master_id", "师父ID", "int", ""), ("apprentice_id", "徒弟ID", "int", ""), ("reason", "原因", "text", "手动解除")], "handler": self.op_mentor_dissolve},
                    "list_relations": {"label": "查看师徒关系", "hint": "MentorshipSystem.list_relations", "fields": [], "handler": self.op_mentor_list},
                    "mentor_info": {"label": "查看良师信息", "hint": "Mentor rank info", "fields": [("player_id", "玩家ID", "int", "")], "handler": self.op_mentor_info},
                    "auto_graduate": {"label": "自动毕业检查", "hint": "MentorshipSystem.auto_graduate_if_needed", "fields": [("apprentice_id", "徒弟ID", "int", "")], "handler": self.op_mentor_auto_graduate},
                    "auto_cleanup": {"label": "离线自动解除", "hint": "MentorshipSystem.auto_cleanup_inactive", "fields": [], "handler": self.op_mentor_auto_cleanup},
                    "team_exp_bonus": {"label": "师徒经验加成", "hint": "MentorshipSystem.team_exp_bonus", "fields": [("master_id", "师父ID", "int", ""), ("apprentice_id", "徒弟ID", "int", "")], "handler": self.op_mentor_bonus},
                },
            },
            "jieyi": {
                "title": "结义系统",
                "operations": {
                    "create_group": {"label": "发起结义", "hint": "BrotherhoodSystem.create_group", "fields": [("member_ids", "成员ID列表(逗号分隔)", "text", ""), ("all_agree", "全员同意(y/n)", "bool", "y"), ("group_name", "结义名号", "text", "江湖金兰"), ("titles", "称号映射(可空, 例 1:大哥)", "text", "")], "handler": self.op_jieyi_create},
                    "leave_group": {"label": "退出结义", "hint": "BrotherhoodSystem.leave_group", "fields": [("player_id", "玩家ID", "int", "")], "handler": self.op_jieyi_leave},
                    "disband_group": {"label": "解散结义", "hint": "BrotherhoodSystem.disband_group", "fields": [("operator_id", "操作者ID", "int", ""), ("confirm", "确认(y/n)", "bool", "y")], "handler": self.op_jieyi_disband},
                    "list_groups": {"label": "查看结义列表", "hint": "BrotherhoodSystem.list_groups", "fields": [], "handler": self.op_jieyi_list},
                    "team_exp_bonus": {"label": "结义经验加成", "hint": "BrotherhoodSystem.team_exp_bonus", "fields": [("team_ids", "队伍ID列表(逗号分隔)", "text", "")], "handler": self.op_jieyi_bonus},
                },
            },
            "romance": {
                "title": "结缘系统",
                "operations": {
                    "add_intimacy_action": {"label": "提升亲密度行为", "hint": "RomanceSystem.add_intimacy_action", "fields": [("a_id", "玩家A", "int", ""), ("b_id", "玩家B", "int", ""), ("action", "行为(组队/私聊/互赠礼物)", "text", "组队")], "handler": self.op_romance_add_intimacy},
                    "bind": {"label": "发起结缘", "hint": "RomanceSystem.bind", "fields": [("a_id", "玩家A", "int", ""), ("b_id", "玩家B", "int", ""), ("both_agree", "双方同意(y/n)", "bool", "y")], "handler": self.op_romance_bind},
                    "dissolve": {"label": "解除结缘", "hint": "RomanceSystem.dissolve", "fields": [("a_id", "玩家A", "int", ""), ("b_id", "玩家B", "int", ""), ("mode", "模式(协议/单方)", "text", "协议")], "handler": self.op_romance_dissolve},
                    "get_intimacy_stage": {"label": "查看亲密阶段", "hint": "RomanceSystem.get_intimacy_stage", "fields": [("a_id", "玩家A", "int", ""), ("b_id", "玩家B", "int", "")], "handler": self.op_romance_stage},
                    "check_condition": {"label": "检查结缘条件", "hint": "RomanceSystem.check_condition", "fields": [("a_id", "玩家A", "int", ""), ("b_id", "玩家B", "int", "")], "handler": self.op_romance_check_condition},
                    "drop_bonus": {"label": "侠侣掉落加成", "hint": "RomanceSystem.drop_bonus", "fields": [("a_id", "玩家A", "int", ""), ("b_id", "玩家B", "int", "")], "handler": self.op_romance_drop_bonus},
                },
            },
            "guild": {
                "title": "帮派系统",
                "operations": {
                    "create_guild": {"label": "创建帮派", "hint": "GuildSystem.create_guild", "fields": [("creator_id", "创建者ID", "int", ""), ("guild_name", "帮派名称", "text", "无名帮")], "handler": self.op_guild_create},
                    "apply_join": {"label": "申请入帮", "hint": "GuildSystem.apply_join", "fields": [("player_id", "玩家ID", "int", ""), ("guild_id", "帮派ID", "int", "")], "handler": self.op_guild_apply},
                    "review_application": {"label": "审批入帮", "hint": "GuildSystem.review_application", "fields": [("admin_id", "审批者ID", "int", ""), ("guild_id", "帮派ID", "int", ""), ("target_player_id", "申请玩家ID", "int", ""), ("accept", "同意(y/n)", "bool", "y")], "handler": self.op_guild_review},
                    "list_guild": {"label": "查看帮派信息", "hint": "GuildSystem.list_guild", "fields": [("guild_id", "帮派ID", "int", "")], "handler": self.op_guild_list},
                    "edit_notice": {"label": "编辑帮派公告", "hint": "GuildSystem.edit_notice", "fields": [("operator_id", "操作者ID", "int", ""), ("guild_id", "帮派ID", "int", ""), ("new_notice", "新公告", "text", "")], "handler": self.op_guild_notice},
                    "complete_daily_task": {"label": "完成帮派日常", "hint": "GuildSystem.complete_daily_task", "fields": [("player_id", "玩家ID", "int", "")], "handler": self.op_guild_daily},
                    "assign_role": {"label": "职务分配", "hint": "GuildSystem.assign_role", "fields": [("leader_id", "帮主ID", "int", ""), ("target_id", "目标成员ID", "int", ""), ("role", "角色(deputy/elder/member)", "text", "member")], "handler": self.op_guild_assign_role},
                    "kick_member": {"label": "踢出成员", "hint": "GuildSystem.kick_member", "fields": [("operator_id", "操作者ID", "int", ""), ("target_id", "目标成员ID", "int", "")], "handler": self.op_guild_kick},
                    "leave_guild": {"label": "主动退帮", "hint": "GuildSystem.leave_guild", "fields": [("player_id", "玩家ID", "int", "")], "handler": self.op_guild_leave},
                    "disband_guild": {"label": "解散帮派", "hint": "GuildSystem.disband_guild", "fields": [("leader_id", "帮主ID", "int", ""), ("confirm", "确认(y/n)", "bool", "y")], "handler": self.op_guild_disband},
                },
            },
            "system": {
                "title": "系统时间",
                "operations": {
                    "advance_day": {"label": "推进系统时间", "hint": "SocialSystem.advance_day", "fields": [("days", "推进天数", "int", "1")], "handler": self.op_advance_day},
                    "current_day": {"label": "查看当前系统日", "hint": "SocialSystem.get_current_day", "fields": [], "handler": self.op_current_day},
                },
            },
        }

    def switch_module(self, module_key: str) -> None:
        if module_key not in self.modules:
            self.log(f"未知模块：{module_key}")
            return

        self.current_module_key = module_key
        module_conf = self.modules[module_key]

        self.module_title.config(text=module_conf["title"])
        self._refresh_day_label()

        op_items = list(module_conf["operations"].items())
        labels = [f"{i + 1}. {op_conf['label']}" for i, (_, op_conf) in enumerate(op_items)]
        self.operation_combo["values"] = labels

        if labels:
            self.operation_combo.current(0)
            self.current_operation_key = op_items[0][0]
            self._render_operation_form()

        self.log(f"已切换模块：{module_conf['title']}")

    def _on_operation_changed(self, _event) -> None:
        module_conf = self.modules[self.current_module_key]
        op_keys = list(module_conf["operations"].keys())
        idx = self.operation_combo.current()
        if idx < 0 or idx >= len(op_keys):
            return
        self.current_operation_key = op_keys[idx]
        self._render_operation_form()

    def _render_operation_form(self) -> None:
        for child in self.form_frame.winfo_children():
            child.destroy()
        self.entry_widgets.clear()

        op_conf = self.modules[self.current_module_key]["operations"][self.current_operation_key]
        self.operation_hint.config(text=op_conf.get("hint", ""))

        fields = op_conf.get("fields", [])
        if not fields:
            ttk.Label(self.form_frame, text="该操作无需输入参数。", style="Hint.TLabel").grid(row=0, column=0, sticky="w", pady=6)
            return

        for i, (field_key, field_label, _field_type, default) in enumerate(fields):
            ttk.Label(self.form_frame, text=field_label).grid(row=i, column=0, sticky="w", padx=(0, 10), pady=5)
            entry = ttk.Entry(self.form_frame)
            entry.grid(row=i, column=1, sticky="ew", pady=5)
            if default:
                entry.insert(0, default)
            self.entry_widgets[field_key] = entry

    def _read_raw(self, key: str, required: bool = True) -> str:
        widget = self.entry_widgets.get(key)
        if widget is None:
            if required:
                raise ValueError(f"缺少字段：{key}")
            return ""
        value = widget.get().strip()
        if required and value == "":
            raise ValueError(f"字段不能为空：{key}")
        return value

    def _read_int(self, key: str) -> int:
        return int(self._read_raw(key, required=True))

    def _read_bool(self, key: str, default: bool = False) -> bool:
        raw = self._read_raw(key, required=False).lower()
        if raw == "":
            return default
        return raw in {"y", "yes", "true", "1", "是"}

    @staticmethod
    def _parse_id_list(raw: str) -> List[int]:
        out = []
        for part in raw.split(","):
            p = part.strip()
            if p:
                out.append(int(p))
        return out

    @staticmethod
    def _parse_titles(raw: str) -> Dict[int, str]:
        out: Dict[int, str] = {}
        if not raw.strip():
            return out
        for seg in raw.split(","):
            item = seg.strip()
            if not item or ":" not in item:
                continue
            k, v = item.split(":", 1)
            out[int(k.strip())] = v.strip()
        return out

    def run_current_operation(self) -> None:
        try:
            op_conf = self.modules[self.current_module_key]["operations"][self.current_operation_key]
            result = op_conf["handler"]()
            self._refresh_day_label()
            self._log_result(result)
        except Exception as exc:
            self.log(f"执行失败：{exc}")

    def _log_result(self, result) -> None:
        if isinstance(result, list):
            self._log_lines(result)
        else:
            self.log(str(result))

    def clear_inputs(self) -> None:
        for widget in self.entry_widgets.values():
            widget.delete(0, "end")

    def _refresh_day_label(self) -> None:
        self.day_label.config(text=f"当前系统日：第 {self.system.get_current_day()} 天")

    def log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message.rstrip() + "\n" + "-" * 62 + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _log_lines(self, lines: List[str]) -> None:
        if not lines:
            self.log("(空结果)")
            return
        self.log("\n".join(lines))

    # Player
    def op_create_player(self) -> str:
        return self.system.create_player(self._read_int("player_id"), self._read_raw("nickname"), self._read_int("level"))

    def op_list_players(self) -> List[str]:
        return self.system.list_players()

    def op_set_online(self) -> str:
        return self.system.set_online(self._read_int("player_id"), self._read_bool("online", default=True))

    def op_set_level(self) -> str:
        return self.system.set_level(self._read_int("player_id"), self._read_int("new_level"))

    # Friend
    def op_friend_send_request(self) -> str:
        return self.system.friend_system.send_request(self._read_int("from_id"), self._read_int("to_id"))

    def op_friend_respond(self) -> str:
        return self.system.friend_system.respond_request(self._read_int("target_id"), self._read_int("requester_id"), self._read_bool("accept", default=True))

    def op_friend_increase_intimacy(self) -> str:
        a_id = self._read_int("a_id")
        b_id = self._read_int("b_id")
        action = self._read_raw("action", required=False)

        amount_raw = self._read_raw("amount", required=False)
        reason_raw = self._read_raw("reason", required=False)

        if amount_raw:
            amount = int(amount_raw)
            reason = reason_raw if reason_raw else (action or "自定义")
            return self.system.friend_system.increase_intimacy(a_id, b_id, amount, reason)

        mapping = {
            "组队": (20, "组队"),
            "私聊": (8, "私聊"),
            "任务": (25, "一起任务"),
            "一起任务": (25, "一起任务"),
            "team": (20, "组队"),
            "chat": (8, "私聊"),
            "task": (25, "一起任务"),
        }
        if action not in mapping:
            return "行为无效，可用：组队/私聊/任务，或填写自定义增量。"

        amount, reason = mapping[action]
        return self.system.friend_system.increase_intimacy(a_id, b_id, amount, reason)

    def op_friend_view_list(self) -> List[str]:
        return self.system.friend_system.view_friend_list(self._read_int("player_id"))

    def op_friend_remove(self) -> str:
        return self.system.friend_system.remove_friend(self._read_int("a_id"), self._read_int("b_id"))

    def op_friend_block_interface(self) -> str:
        return self.system.friend_system.reserve_block_interface(self._read_int("player_id"), self._read_int("target_id"))

    # Mentor
    def op_mentor_bind(self) -> str:
        return self.system.mentor_system.bind(self._read_int("master_id"), self._read_int("apprentice_id"))

    def op_mentor_daily(self) -> str:
        return self.system.mentor_system.complete_daily_task(self._read_int("master_id"), self._read_int("apprentice_id"), self._read_bool("teamed", default=True))

    def op_mentor_weekly(self) -> str:
        return self.system.mentor_system.complete_weekly_task(self._read_int("master_id"), self._read_int("apprentice_id"), self._read_bool("teamed", default=True))

    def op_mentor_dissolve(self) -> str:
        reason = self._read_raw("reason", required=False) or "手动解除"
        return self.system.mentor_system.dissolve(self._read_int("master_id"), self._read_int("apprentice_id"), reason)

    def op_mentor_list(self) -> List[str]:
        return self.system.mentor_system.list_relations()

    def op_mentor_info(self) -> str:
        pid = self._read_int("player_id")
        if pid not in self.system.players:
            return "玩家不存在。"
        p = self.system.players[pid]
        rank_name = MentorshipSystem.RANKS[p.mentor_rank - 1]
        return f"良师值={p.mentor_value}，良师等级={rank_name}（{p.mentor_rank}/5）"

    def op_mentor_auto_graduate(self) -> List[str]:
        return self.system.mentor_system.auto_graduate_if_needed(self._read_int("apprentice_id"))

    def op_mentor_auto_cleanup(self) -> List[str]:
        return self.system.mentor_system.auto_cleanup_inactive()

    def op_mentor_bonus(self) -> str:
        bonus = self.system.mentor_system.team_exp_bonus(self._read_int("master_id"), self._read_int("apprentice_id"))
        return f"师徒经验加成倍率：{bonus:.2f}"

    # Jieyi
    def op_jieyi_create(self) -> str:
        if not self._read_bool("all_agree", default=True):
            return "已取消：存在成员未同意。"

        ids = self._parse_id_list(self._read_raw("member_ids"))
        if not ids:
            return "成员ID输入无效。"

        name = self._read_raw("group_name", required=False) or "江湖金兰"
        titles = self._parse_titles(self._read_raw("titles", required=False))
        if not titles:
            titles = {pid: "金兰侠士" for pid in ids}

        return self.system.brotherhood_system.create_group(ids, name, titles)

    def op_jieyi_leave(self) -> str:
        return self.system.brotherhood_system.leave_group(self._read_int("player_id"))

    def op_jieyi_disband(self) -> str:
        if not self._read_bool("confirm", default=False):
            return "已取消。"
        return self.system.brotherhood_system.disband_group(self._read_int("operator_id"))

    def op_jieyi_list(self) -> List[str]:
        return self.system.brotherhood_system.list_groups()

    def op_jieyi_bonus(self) -> str:
        ids = self._parse_id_list(self._read_raw("team_ids"))
        bonus = self.system.brotherhood_system.team_exp_bonus(ids)
        return f"结义经验加成倍率：{bonus:.2f}"

    # Romance
    def op_romance_add_intimacy(self) -> str:
        return self.system.romance_system.add_intimacy_action(self._read_int("a_id"), self._read_int("b_id"), self._read_raw("action"))

    def op_romance_bind(self) -> str:
        if not self._read_bool("both_agree", default=True):
            return "结缘失败：双方未同意。"
        return self.system.romance_system.bind(self._read_int("a_id"), self._read_int("b_id"))

    def op_romance_dissolve(self) -> str:
        mode = self._read_raw("mode", required=False) or "协议"
        return self.system.romance_system.dissolve(self._read_int("a_id"), self._read_int("b_id"), mode)

    def op_romance_stage(self) -> str:
        a_id = self._read_int("a_id")
        b_id = self._read_int("b_id")
        stage = self.system.romance_system.get_intimacy_stage(a_id, b_id)
        intimacy = 0
        if a_id in self.system.players:
            intimacy = self.system.players[a_id].friend_intimacy.get(b_id, 0)
        return f"当前亲密度={intimacy}，阶段={stage}"

    def op_romance_check_condition(self) -> str:
        ok, msg = self.system.romance_system.check_condition(self._read_int("a_id"), self._read_int("b_id"))
        return f"可结缘={ok}；说明：{msg}"

    def op_romance_drop_bonus(self) -> str:
        bonus = self.system.romance_system.drop_bonus(self._read_int("a_id"), self._read_int("b_id"))
        return f"侠侣掉落加成倍率：{bonus:.2f}"

    # Guild
    def op_guild_create(self) -> str:
        name = self._read_raw("guild_name", required=False) or "无名帮"
        return self.system.guild_system.create_guild(self._read_int("creator_id"), name)

    def op_guild_apply(self) -> str:
        return self.system.guild_system.apply_join(self._read_int("player_id"), self._read_int("guild_id"))

    def op_guild_review(self) -> str:
        return self.system.guild_system.review_application(self._read_int("admin_id"), self._read_int("guild_id"), self._read_int("target_player_id"), self._read_bool("accept", default=True))

    def op_guild_list(self) -> List[str]:
        return self.system.guild_system.list_guild(self._read_int("guild_id"))

    def op_guild_notice(self) -> str:
        return self.system.guild_system.edit_notice(self._read_int("operator_id"), self._read_int("guild_id"), self._read_raw("new_notice"))

    def op_guild_daily(self) -> str:
        return self.system.guild_system.complete_daily_task(self._read_int("player_id"))

    def op_guild_assign_role(self) -> str:
        return self.system.guild_system.assign_role(self._read_int("leader_id"), self._read_int("target_id"), self._read_raw("role"))

    def op_guild_kick(self) -> str:
        return self.system.guild_system.kick_member(self._read_int("operator_id"), self._read_int("target_id"))

    def op_guild_leave(self) -> str:
        return self.system.guild_system.leave_guild(self._read_int("player_id"))

    def op_guild_disband(self) -> str:
        if not self._read_bool("confirm", default=False):
            return "已取消。"
        return self.system.guild_system.disband_guild(self._read_int("leader_id"))

    # System
    def op_advance_day(self) -> str:
        return self.system.advance_day(self._read_int("days"))

    def op_current_day(self) -> str:
        return f"当前系统日：第 {self.system.get_current_day()} 天"

    def init_demo_data(self) -> None:
        logs: List[str] = []

        presets: List[Tuple[int, str, int]] = [
            (1001, "少侠甲", 35),
            (1002, "少侠乙", 42),
            (1003, "名师丙", 72),
            (1004, "金兰丁", 41),
            (1005, "帮主戊", 65),
            (1006, "新秀己", 28),
        ]
        for pid, name, level in presets:
            logs.append(self.system.create_player(pid, name, level))

        def add_friend(a: int, b: int) -> None:
            logs.append(self.system.friend_system.send_request(a, b))
            logs.append(self.system.friend_system.respond_request(b, a, True))

        add_friend(1001, 1002)
        add_friend(1001, 1004)
        add_friend(1002, 1004)

        logs.append(self.system.friend_system.increase_intimacy(1001, 1002, 600, "演示初始化"))
        logs.append(self.system.mentor_system.bind(1003, 1001))

        logs.append(self.system.guild_system.create_guild(1005, "演示帮派"))
        leader = self.system.players.get(1005)
        gid = leader.guild_id if leader else None
        if gid is not None:
            logs.append(self.system.guild_system.apply_join(1006, gid))
            logs.append(self.system.guild_system.review_application(1005, gid, 1006, True))

        self._log_lines(logs)
        self._refresh_day_label()

    def run(self) -> None:
        self.log("GUI 已启动，中文显示已修复。")
        self.root.mainloop()


def main() -> None:
    app = SocialSystemGUI()
    app.run()


if __name__ == "__main__":
    main()
