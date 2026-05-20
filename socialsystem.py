# social_system_new.py
# -*- coding: utf-8 -*-

"""
仿武侠 MMO 社交系统白盒（命令行交互版）
- 内存存储，无数据库
- 面向对象分层：Player -> 关系实体 -> 子系统 -> 总控系统
- 模块：
  1) 基础好友系统
  2) 师徒系统
  3) 结义金兰系统
  4) 侠侣结缘系统
  5) 帮派帮会系统

说明：
1. 本实现用于“策划白盒学习/面试演示”，规则尽量贴近你给出的逆水寒式约束。
2. 商业游戏存在大量隐藏参数与服务端联动，本代码以可演示、可扩展为目标。
"""

from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional, Tuple


# =========================
# 1) 玩家基础实体
# =========================
@dataclass
class Player:
    """玩家基础信息实体：所有社交系统共享的数据都挂在玩家上。"""
    player_id: int
    nickname: str
    level: int
    online: bool = True

    # 用于“长期不在线自动解除关系”等规则
    last_online_day: int = 0

    # 好友系统
    friend_groups: Dict[str, Set[int]] = field(default_factory=lambda: {"默认分组": set()})
    friend_intimacy: Dict[int, int] = field(default_factory=dict)
    blocked_players: Set[int] = field(default_factory=set)  # 预留拉黑

    # 师徒系统字段
    master_ids: Set[int] = field(default_factory=set)      # 徒弟最多 2 名师父
    apprentice_ids: Set[int] = field(default_factory=set)  # 师父最多 3 名徒弟
    mentor_value: int = 0
    mentor_rank: int = 1  # 1~5：初阶/中阶/高阶/名师/宗师

    # 结义
    jieyi_group_id: Optional[int] = None
    jieyi_cooldown_until: int = 0

    # 侠侣
    lover_id: Optional[int] = None
    lover_cooldown_until: int = 0

    # 帮派
    guild_id: Optional[int] = None
    guild_role: Optional[str] = None  # leader/deputy/elder/member
    guild_cooldown_until: int = 0

    # 资源
    coins: int = 10000

    def is_friend(self, other_id: int) -> bool:
        return other_id in self.friend_groups.get("默认分组", set())


# =========================
# 2) 关系实体类
# =========================
@dataclass
class MentorshipRelation:
    relation_id: int
    master_id: int
    apprentice_id: int
    created_day: int
    active: bool = True
    last_daily_task_day: int = -1
    last_weekly_task_week: int = -1


@dataclass
class JieyiGroup:
    group_id: int
    name: str
    members: Set[int]
    titles: Dict[int, str]    # 每个成员的结义称号
    created_day: int
    chat_history: List[str] = field(default_factory=list)


@dataclass
class RomanceRelation:
    relation_id: int
    player_a: int
    player_b: int
    created_day: int
    chat_history: List[str] = field(default_factory=list)


@dataclass
class Guild:
    guild_id: int
    name: str
    leader_id: int
    deputy_ids: Set[int] = field(default_factory=set)
    elder_ids: Set[int] = field(default_factory=set)
    member_ids: Set[int] = field(default_factory=set)
    applications: Set[int] = field(default_factory=set)
    notice: str = "欢迎加入本帮派。"
    activity: int = 0
    chat_history: List[str] = field(default_factory=list)


# =========================
# 3) 子系统：好友系统
# =========================
class FriendSystem:
    """
    好友规则：
    - 申请->同意后双向绑定
    - 亲密度双向同步
    - 删除好友后清空亲密度
    """
    def __init__(self, players: Dict[int, Player]):
        self.players = players
        self.pending_requests: Dict[int, Set[int]] = {}  # target_id -> {requester_id}

    def send_request(self, from_id: int, to_id: int) -> str:
        if from_id == to_id:
            return "不能添加自己为好友。"
        if from_id not in self.players or to_id not in self.players:
            return "玩家不存在。"
        a, b = self.players[from_id], self.players[to_id]
        if to_id in a.blocked_players or from_id in b.blocked_players:
            return "存在拉黑关系，无法申请好友。"
        if a.is_friend(to_id):
            return "你们已经是好友。"

        self.pending_requests.setdefault(to_id, set()).add(from_id)
        return f"好友申请已发送给 {b.nickname}({to_id})。"

    def respond_request(self, target_id: int, requester_id: int, accept: bool) -> str:
        if target_id not in self.players or requester_id not in self.players:
            return "玩家不存在。"

        reqs = self.pending_requests.get(target_id, set())
        if requester_id not in reqs:
            return "未找到该好友申请。"

        reqs.remove(requester_id)
        if not reqs:
            self.pending_requests.pop(target_id, None)

        if not accept:
            return "已拒绝好友申请。"

        self._bind_friendship(requester_id, target_id)
        return "已同意好友申请，双方成为好友。"

    def _bind_friendship(self, a_id: int, b_id: int) -> None:
        a, b = self.players[a_id], self.players[b_id]
        a.friend_groups.setdefault("默认分组", set()).add(b_id)
        b.friend_groups.setdefault("默认分组", set()).add(a_id)
        a.friend_intimacy.setdefault(b_id, 0)
        b.friend_intimacy.setdefault(a_id, 0)

    def increase_intimacy(self, a_id: int, b_id: int, amount: int, reason: str) -> str:
        if amount <= 0:
            return "亲密度增量必须大于 0。"
        if a_id not in self.players or b_id not in self.players:
            return "玩家不存在。"

        a, b = self.players[a_id], self.players[b_id]
        if not a.is_friend(b_id):
            return "非好友关系，无法增加亲密度。"

        a.friend_intimacy[b_id] = a.friend_intimacy.get(b_id, 0) + amount
        b.friend_intimacy[a_id] = b.friend_intimacy.get(a_id, 0) + amount
        return f"因[{reason}]，双方亲密度 +{amount}。"

    def remove_friend(self, a_id: int, b_id: int) -> str:
        if a_id not in self.players or b_id not in self.players:
            return "玩家不存在。"

        a, b = self.players[a_id], self.players[b_id]
        existed = False

        for p, other in ((a, b_id), (b, a_id)):
            if other in p.friend_groups.get("默认分组", set()):
                p.friend_groups["默认分组"].remove(other)
                existed = True
            p.friend_intimacy.pop(other, None)

        if not existed:
            return "双方原本不是好友。"
        return "已删除好友，亲密度已清空。"

    def view_friend_list(self, player_id: int) -> List[str]:
        if player_id not in self.players:
            return ["玩家不存在。"]

        p = self.players[player_id]
        result = []
        for fid in sorted(p.friend_groups.get("默认分组", set())):
            fp = self.players.get(fid)
            if not fp:
                continue
            intimacy = p.friend_intimacy.get(fid, 0)
            status = "在线" if fp.online else "离线"
            result.append(f"ID={fid} 昵称={fp.nickname} 等级={fp.level} 状态={status} 亲密度={intimacy}")
        if not result:
            result.append("暂无好友。")
        return result

    def reserve_block_interface(self, player_id: int, target_id: int) -> str:
        # 预留接口：本白盒不做完整拉黑流程，仅保留扩展位
        return "拉黑功能接口已预留，可在后续版本接入屏蔽聊天/拒绝申请等逻辑。"


# =========================
# 4) 子系统：师徒系统
# =========================
class MentorshipSystem:
    """
    规则：
    1) 准入：师父>=60，徒弟<=59，等级差>=7
    2) 数量：徒弟最多2师父；师父最多3徒弟
    3) 良师体系：5级，良师值升级
    4) 每日/周常师徒任务：必须组队且都在线
    5) 徒弟>=60自动毕业，发奖励并解除关系
    6) 手动解除/长期离线自动解除，带冷却
    """
    RANKS = ["初阶", "中阶", "高阶", "名师", "宗师"]
    RANK_THRESHOLDS = [0, 100, 300, 700, 1500]  # mentor_value 到达阈值升级
    DISSOLVE_COOLDOWN_DAYS = 3
    INACTIVE_DISSOLVE_DAYS = 30

    def __init__(self, players: Dict[int, Player], get_current_day):
        self.players = players
        self.get_current_day = get_current_day
        self.relations: Dict[int, MentorshipRelation] = {}
        self.pair_to_relation_id: Dict[Tuple[int, int], int] = {}  # (master, apprentice) -> relation_id
        self.next_relation_id = 1
        self.dissolve_cooldown: Dict[Tuple[int, int], int] = {}

    def _pair(self, master_id: int, apprentice_id: int) -> Tuple[int, int]:
        return (master_id, apprentice_id)

    def can_bind(self, master_id: int, apprentice_id: int) -> Tuple[bool, str]:
        if master_id == apprentice_id:
            return False, "不能与自己建立师徒。"
        if master_id not in self.players or apprentice_id not in self.players:
            return False, "玩家不存在。"

        master = self.players[master_id]
        apprentice = self.players[apprentice_id]

        if master.level < 60:
            return False, "师父等级需 >= 60。"
        if apprentice.level > 59:
            return False, "徒弟等级需 <= 59。"
        if master.level - apprentice.level < 7:
            return False, "师徒等级差需 >= 7。"

        if len(apprentice.master_ids) >= 2:
            return False, "徒弟最多可拜 2 名师父。"
        if len(master.apprentice_ids) >= 3:
            return False, "师父最多可收 3 名徒弟。"

        if (master_id, apprentice_id) in self.pair_to_relation_id:
            return False, "该师徒关系已存在。"

        cd_until = self.dissolve_cooldown.get(self._pair(master_id, apprentice_id), 0)
        if self.get_current_day() < cd_until:
            return False, f"该对师徒关系处于解除冷却中，冷却到第 {cd_until} 天。"

        return True, "可以建立师徒关系。"

    def bind(self, master_id: int, apprentice_id: int) -> str:
        ok, msg = self.can_bind(master_id, apprentice_id)
        if not ok:
            return msg

        rid = self.next_relation_id
        self.next_relation_id += 1

        rel = MentorshipRelation(
            relation_id=rid,
            master_id=master_id,
            apprentice_id=apprentice_id,
            created_day=self.get_current_day()
        )
        self.relations[rid] = rel
        self.pair_to_relation_id[(master_id, apprentice_id)] = rid

        self.players[master_id].apprentice_ids.add(apprentice_id)
        self.players[apprentice_id].master_ids.add(master_id)

        return f"师徒关系建立成功：师父 {master_id} -> 徒弟 {apprentice_id}。"

    def _add_mentor_value(self, master_id: int, delta: int) -> None:
        p = self.players[master_id]
        p.mentor_value += delta

        # 按阈值刷新良师等级（1~5）
        new_rank = 1
        for i, th in enumerate(self.RANK_THRESHOLDS, start=1):
            if p.mentor_value >= th:
                new_rank = i
        p.mentor_rank = min(5, new_rank)

    def complete_daily_task(self, master_id: int, apprentice_id: int, teamed: bool) -> str:
        pair = (master_id, apprentice_id)
        rid = self.pair_to_relation_id.get(pair)
        if not rid:
            return "该师徒关系不存在。"

        rel = self.relations[rid]
        if not rel.active:
            return "该师徒关系已失效。"

        if not teamed:
            return "每日师徒任务必须师徒组队完成。"

        m, a = self.players[master_id], self.players[apprentice_id]
        if not (m.online and a.online):
            return "师徒双方需在线才可完成任务。"

        today = self.get_current_day()
        if rel.last_daily_task_day == today:
            return "今日已完成该对师徒每日任务。"

        rel.last_daily_task_day = today
        self._add_mentor_value(master_id, 15)

        # 白盒演示：任务奖励
        m.coins += 100
        a.coins += 150
        return "每日师徒任务完成：师父+15良师值，双方获得奖励。"

    def complete_weekly_task(self, master_id: int, apprentice_id: int, teamed: bool) -> str:
        pair = (master_id, apprentice_id)
        rid = self.pair_to_relation_id.get(pair)
        if not rid:
            return "该师徒关系不存在。"

        rel = self.relations[rid]
        if not rel.active:
            return "该师徒关系已失效。"

        if not teamed:
            return "周常师徒任务必须师徒组队完成。"

        m, a = self.players[master_id], self.players[apprentice_id]
        if not (m.online and a.online):
            return "师徒双方需在线才可完成任务。"

        week_idx = self.get_current_day() // 7
        if rel.last_weekly_task_week == week_idx:
            return "本周已完成该对师徒周常任务。"

        rel.last_weekly_task_week = week_idx
        self._add_mentor_value(master_id, 50)
        m.coins += 300
        a.coins += 350
        return "周常师徒任务完成：师父+50良师值，双方获得奖励。"

    def dissolve(self, master_id: int, apprentice_id: int, reason: str) -> str:
        rid = self.pair_to_relation_id.get((master_id, apprentice_id))
        if not rid:
            return "师徒关系不存在。"

        rel = self.relations[rid]
        rel.active = False

        self.players[master_id].apprentice_ids.discard(apprentice_id)
        self.players[apprentice_id].master_ids.discard(master_id)

        self.pair_to_relation_id.pop((master_id, apprentice_id), None)

        # 冷却限制：解除后短期内不能立刻重新建立
        cd_until = self.get_current_day() + self.DISSOLVE_COOLDOWN_DAYS
        self.dissolve_cooldown[(master_id, apprentice_id)] = cd_until

        return f"师徒关系已解除，原因：{reason}。冷却至第 {cd_until} 天。"

    def auto_graduate_if_needed(self, apprentice_id: int) -> List[str]:
        """徒弟升级触发：达到 60 自动毕业。"""
        messages = []
        if apprentice_id not in self.players:
            return ["玩家不存在。"]

        apprentice = self.players[apprentice_id]
        if apprentice.level < 60:
            return ["徒弟未达毕业等级。"]

        master_ids = list(apprentice.master_ids)
        for mid in master_ids:
            self._add_mentor_value(mid, 80)
            self.players[mid].coins += 500
            apprentice.coins += 500
            msg = self.dissolve(mid, apprentice_id, "徒弟达到60级自动毕业")
            messages.append(f"{msg} 已发放毕业奖励。")
        if not messages:
            messages.append("该玩家当前无师徒关系可毕业。")
        return messages

    def auto_cleanup_inactive(self) -> List[str]:
        """
        长期不在线自动解除：
        - 任一方离线超过阈值天数，关系自动解除
        """
        today = self.get_current_day()
        messages = []
        to_dissolve = []

        for rid, rel in self.relations.items():
            if not rel.active:
                continue
            master = self.players[rel.master_id]
            apprentice = self.players[rel.apprentice_id]
            m_offline_days = today - master.last_online_day if not master.online else 0
            a_offline_days = today - apprentice.last_online_day if not apprentice.online else 0
            if m_offline_days >= self.INACTIVE_DISSOLVE_DAYS or a_offline_days >= self.INACTIVE_DISSOLVE_DAYS:
                to_dissolve.append((rel.master_id, rel.apprentice_id))

        for m, a in to_dissolve:
            messages.append(self.dissolve(m, a, "长期不在线自动解除"))

        return messages if messages else ["无自动解除项。"]

    def team_exp_bonus(self, master_id: int, apprentice_id: int) -> float:
        """师徒组队经验加成示意。"""
        if (master_id, apprentice_id) in self.pair_to_relation_id:
            return 1.10
        return 1.00

    def list_relations(self) -> List[str]:
        out = []
        for rid, rel in self.relations.items():
            if not rel.active:
                continue
            m = self.players[rel.master_id]
            a = self.players[rel.apprentice_id]
            out.append(
                f"RID={rid} 师父={m.nickname}({m.player_id}) 徒弟={a.nickname}({a.player_id}) 创建日={rel.created_day}"
            )
        return out if out else ["暂无有效师徒关系。"]


# =========================
# 5) 子系统：结义金兰系统
# =========================
class BrotherhoodSystem:
    """
    规则：
    - 2~5人
    - 全员互为好友
    - 全员>=30级
    - 成员无结义冲突（不能已有结义）
    - 退出/解散后冷却
    """
    COOLDOWN_DAYS = 3

    def __init__(self, players: Dict[int, Player], get_current_day):
        self.players = players
        self.get_current_day = get_current_day
        self.groups: Dict[int, JieyiGroup] = {}
        self.next_group_id = 1

    def _all_mutual_friends(self, member_ids: List[int]) -> bool:
        for i in range(len(member_ids)):
            for j in range(i + 1, len(member_ids)):
                a, b = self.players[member_ids[i]], self.players[member_ids[j]]
                if not (a.is_friend(b.player_id) and b.is_friend(a.player_id)):
                    return False
        return True

    def create_group(self, member_ids: List[int], group_name: str, titles: Dict[int, str]) -> str:
        unique_ids = list(dict.fromkeys(member_ids))
        if len(unique_ids) < 2 or len(unique_ids) > 5:
            return "结义人数必须在 2~5 人。"

        for pid in unique_ids:
            if pid not in self.players:
                return f"玩家 {pid} 不存在。"

        for pid in unique_ids:
            p = self.players[pid]
            if p.level < 30:
                return f"玩家 {pid} 等级不足 30。"
            if p.jieyi_group_id is not None:
                return f"玩家 {pid} 已有结义关系。"
            if self.get_current_day() < p.jieyi_cooldown_until:
                return f"玩家 {pid} 处于结义冷却期至第 {p.jieyi_cooldown_until} 天。"

        if not self._all_mutual_friends(unique_ids):
            return "结义失败：未满足全员互为好友。"

        gid = self.next_group_id
        self.next_group_id += 1
        group = JieyiGroup(
            group_id=gid,
            name=group_name,
            members=set(unique_ids),
            titles={pid: titles.get(pid, "金兰侠士") for pid in unique_ids},
            created_day=self.get_current_day()
        )
        self.groups[gid] = group

        for pid in unique_ids:
            self.players[pid].jieyi_group_id = gid

        return f"结义成功！结义编号={gid}，名号={group_name}。"

    def leave_group(self, player_id: int) -> str:
        if player_id not in self.players:
            return "玩家不存在。"
        p = self.players[player_id]
        gid = p.jieyi_group_id
        if gid is None or gid not in self.groups:
            return "你当前不在任何结义中。"

        group = self.groups[gid]
        group.members.discard(player_id)
        group.titles.pop(player_id, None)
        p.jieyi_group_id = None
        p.jieyi_cooldown_until = self.get_current_day() + self.COOLDOWN_DAYS

        if len(group.members) < 2:
            # 结义最低人数不足时自动解散
            for rest_id in list(group.members):
                self.players[rest_id].jieyi_group_id = None
                self.players[rest_id].jieyi_cooldown_until = self.get_current_day() + self.COOLDOWN_DAYS
            self.groups.pop(gid, None)
            return f"你已退出结义。剩余人数不足 2，结义自动解散。"

        return f"你已退出结义，冷却到第 {p.jieyi_cooldown_until} 天。"

    def disband_group(self, operator_id: int) -> str:
        if operator_id not in self.players:
            return "玩家不存在。"

        p = self.players[operator_id]
        gid = p.jieyi_group_id
        if gid is None or gid not in self.groups:
            return "你当前不在结义中。"

        group = self.groups[gid]
        for pid in list(group.members):
            self.players[pid].jieyi_group_id = None
            self.players[pid].jieyi_cooldown_until = self.get_current_day() + self.COOLDOWN_DAYS
        self.groups.pop(gid, None)

        return f"结义 {gid} 已解散，全员进入冷却。"

    def team_exp_bonus(self, team_ids: List[int]) -> float:
        # 若队伍中存在同结义成员，给出示意加成
        gids = [self.players[pid].jieyi_group_id for pid in team_ids if pid in self.players]
        gids = [g for g in gids if g is not None]
        if not gids:
            return 1.0
        # 至少2人同结义
        for gid in set(gids):
            if gids.count(gid) >= 2:
                return 1.08
        return 1.0

    def list_groups(self) -> List[str]:
        out = []
        for gid, g in self.groups.items():
            names = ", ".join(f"{self.players[pid].nickname}({pid}:{g.titles.get(pid,'')})" for pid in g.members)
            out.append(f"GID={gid} 名号={g.name} 成员=[{names}]")
        return out if out else ["暂无结义组织。"]


# =========================
# 6) 子系统：侠侣结缘系统
# =========================
class RomanceSystem:
    """
    规则：
    - 一对一唯一
    - 条件：互为好友、等级>=40、亲密度达到阈值、无师徒/结义冲突
    - 解除后清空双方亲密度 + 7天冷却
    """
    COOL_DOWN_DAYS = 7
    REQUIRED_INTIMACY = 500

    # 亲密等级阈值（白盒示例）
    INTIMACY_STAGES = [
        (0, "初识"),
        (300, "相知"),
        (800, "相惜"),
        (1500, "情深"),
        (3000, "生死不离")
    ]

    def __init__(self, players: Dict[int, Player], get_current_day):
        self.players = players
        self.get_current_day = get_current_day
        self.relations: Dict[int, RomanceRelation] = {}
        self.pair_index: Dict[frozenset, int] = {}
        self.next_relation_id = 1

    def _pair_key(self, a: int, b: int) -> frozenset:
        return frozenset({a, b})

    def check_condition(self, a_id: int, b_id: int) -> Tuple[bool, str]:
        if a_id == b_id:
            return False, "不能与自己结缘。"
        if a_id not in self.players or b_id not in self.players:
            return False, "玩家不存在。"

        a, b = self.players[a_id], self.players[b_id]

        if a.lover_id is not None or b.lover_id is not None:
            return False, "双方必须都处于未结缘状态。"

        if a.level < 40 or b.level < 40:
            return False, "双方等级都需 >= 40。"

        if not (a.is_friend(b_id) and b.is_friend(a_id)):
            return False, "双方必须互为好友。"

        intimacy = a.friend_intimacy.get(b_id, 0)
        if intimacy < self.REQUIRED_INTIMACY:
            return False, f"亲密度不足，当前 {intimacy}，要求 {self.REQUIRED_INTIMACY}。"

        # 无师徒冲突：不可为直接师徒
        if b_id in a.master_ids or b_id in a.apprentice_ids:
            return False, "存在师徒冲突，不可结缘。"

        # 无结义冲突：此处采用“同结义成员不可直接转情缘”的演示规则
        if a.jieyi_group_id is not None and a.jieyi_group_id == b.jieyi_group_id:
            return False, "同结义关系冲突，不可结缘。"

        if self.get_current_day() < a.lover_cooldown_until or self.get_current_day() < b.lover_cooldown_until:
            return False, "有一方处于结缘冷却期。"

        return True, "可结缘。"

    def bind(self, a_id: int, b_id: int) -> str:
        ok, msg = self.check_condition(a_id, b_id)
        if not ok:
            return msg

        rid = self.next_relation_id
        self.next_relation_id += 1
        rel = RomanceRelation(rid, a_id, b_id, self.get_current_day())
        self.relations[rid] = rel
        self.pair_index[self._pair_key(a_id, b_id)] = rid

        self.players[a_id].lover_id = b_id
        self.players[b_id].lover_id = a_id

        return f"结缘成功：{a_id} 与 {b_id} 成为侠侣。"

    def get_intimacy_stage(self, a_id: int, b_id: int) -> str:
        if a_id not in self.players or b_id not in self.players:
            return "未知"
        intimacy = self.players[a_id].friend_intimacy.get(b_id, 0)
        stage = "初识"
        for threshold, name in self.INTIMACY_STAGES:
            if intimacy >= threshold:
                stage = name
        return stage

    def add_intimacy_action(self, a_id: int, b_id: int, action: str) -> str:
        if a_id not in self.players or b_id not in self.players:
            return "玩家不存在。"
        if not self.players[a_id].is_friend(b_id):
            return "双方不是好友，无法提升亲密度。"

        gains = {
            "组队": 30,
            "私聊": 15,
            "互赠礼物": 80
        }
        if action not in gains:
            return "无效行为，可选：组队/私聊/互赠礼物。"

        gain = gains[action]
        self.players[a_id].friend_intimacy[b_id] = self.players[a_id].friend_intimacy.get(b_id, 0) + gain
        self.players[b_id].friend_intimacy[a_id] = self.players[b_id].friend_intimacy.get(a_id, 0) + gain

        stage = self.get_intimacy_stage(a_id, b_id)
        return f"[{action}]成功，双方亲密度 +{gain}，当前阶段：{stage}。"

    def dissolve(self, a_id: int, b_id: int, mode: str) -> str:
        key = self._pair_key(a_id, b_id)
        rid = self.pair_index.get(key)
        if not rid:
            return "双方当前不是侠侣关系。"

        self.pair_index.pop(key, None)
        self.relations.pop(rid, None)

        pa, pb = self.players[a_id], self.players[b_id]
        pa.lover_id = None
        pb.lover_id = None

        # 解除清空亲密度（按你的要求）
        pa.friend_intimacy[b_id] = 0
        pb.friend_intimacy[a_id] = 0

        cd = self.get_current_day() + self.COOL_DOWN_DAYS
        pa.lover_cooldown_until = cd
        pb.lover_cooldown_until = cd

        return f"已{mode}解除侠侣关系，亲密度清零，双方冷却至第 {cd} 天。"

    def drop_bonus(self, a_id: int, b_id: int) -> float:
        if a_id in self.players and self.players[a_id].lover_id == b_id:
            return 1.12
        return 1.00


# =========================
# 7) 子系统：帮派帮会系统
# =========================
class GuildSystem:
    """
    规则：
    - 组织结构：帮主/副帮主/长老/帮众
    - 创建：等级达标 + 消耗货币
    - 入帮：申请->审批
    - 功能：频道/成员查看/公告编辑
    - 任务：每日任务 -> 奖励 + 活跃
    - 管理：踢人/退帮/解散，退帮冷却
    """
    CREATE_LEVEL_REQ = 40
    CREATE_COST = 5000
    JOIN_LEVEL_REQ = 20
    LEAVE_CD_DAYS = 2

    def __init__(self, players: Dict[int, Player], get_current_day):
        self.players = players
        self.get_current_day = get_current_day
        self.guilds: Dict[int, Guild] = {}
        self.next_guild_id = 1
        self.last_task_done_day: Dict[Tuple[int, int], int] = {}  # (guild_id, player_id) -> day

    def _is_manager(self, guild: Guild, player_id: int) -> bool:
        return player_id == guild.leader_id or player_id in guild.deputy_ids or player_id in guild.elder_ids

    def create_guild(self, creator_id: int, guild_name: str) -> str:
        if creator_id not in self.players:
            return "玩家不存在。"
        p = self.players[creator_id]

        if p.guild_id is not None:
            return "你已加入帮派，无法重复创建。"
        if p.level < self.CREATE_LEVEL_REQ:
            return f"创建帮派需要等级 >= {self.CREATE_LEVEL_REQ}。"
        if p.coins < self.CREATE_COST:
            return f"货币不足，创建需 {self.CREATE_COST}。"

        p.coins -= self.CREATE_COST
        gid = self.next_guild_id
        self.next_guild_id += 1

        g = Guild(guild_id=gid, name=guild_name, leader_id=creator_id, member_ids={creator_id})
        self.guilds[gid] = g

        p.guild_id = gid
        p.guild_role = "leader"

        return f"帮派创建成功：GID={gid} 名称={guild_name}。"

    def apply_join(self, player_id: int, guild_id: int) -> str:
        if player_id not in self.players:
            return "玩家不存在。"
        if guild_id not in self.guilds:
            return "帮派不存在。"

        p = self.players[player_id]
        if p.guild_id is not None:
            return "你已经在帮派中。"
        if p.level < self.JOIN_LEVEL_REQ:
            return f"入帮等级不足，需 >= {self.JOIN_LEVEL_REQ}。"
        if self.get_current_day() < p.guild_cooldown_until:
            return f"退帮冷却中，冷却至第 {p.guild_cooldown_until} 天。"

        guild = self.guilds[guild_id]
        guild.applications.add(player_id)
        return f"入帮申请已提交到 [{guild.name}]。"

    def review_application(self, admin_id: int, guild_id: int, target_player_id: int, accept: bool) -> str:
        if guild_id not in self.guilds:
            return "帮派不存在。"
        guild = self.guilds[guild_id]

        if admin_id not in self.players or target_player_id not in self.players:
            return "玩家不存在。"
        if self.players[admin_id].guild_id != guild_id:
            return "你不在该帮派。"
        if not self._is_manager(guild, admin_id):
            return "权限不足，需帮主/副帮主/长老。"

        if target_player_id not in guild.applications:
            return "该玩家未申请该帮派。"

        guild.applications.remove(target_player_id)

        if not accept:
            return "已拒绝入帮申请。"

        tp = self.players[target_player_id]
        if tp.guild_id is not None:
            return "该玩家已在其他帮派中。"

        guild.member_ids.add(target_player_id)
        tp.guild_id = guild_id
        tp.guild_role = "member"
        return "已同意入帮申请。"

    def edit_notice(self, operator_id: int, guild_id: int, new_notice: str) -> str:
        if guild_id not in self.guilds:
            return "帮派不存在。"
        g = self.guilds[guild_id]

        if operator_id not in self.players:
            return "玩家不存在。"
        if self.players[operator_id].guild_id != guild_id:
            return "你不在该帮派。"
        if not self._is_manager(g, operator_id):
            return "权限不足，需管理层。"

        g.notice = new_notice
        return "帮派公告已更新。"

    def complete_daily_task(self, player_id: int) -> str:
        if player_id not in self.players:
            return "玩家不存在。"
        p = self.players[player_id]
        if p.guild_id is None or p.guild_id not in self.guilds:
            return "你当前不在帮派中。"

        gid = p.guild_id
        today = self.get_current_day()
        key = (gid, player_id)
        if self.last_task_done_day.get(key, -1) == today:
            return "今日已完成帮派任务。"

        self.last_task_done_day[key] = today
        p.coins += 120
        self.guilds[gid].activity += 10
        return "帮派日常完成：个人获得奖励，帮派活跃度 +10。"

    def kick_member(self, operator_id: int, target_id: int) -> str:
        if operator_id not in self.players or target_id not in self.players:
            return "玩家不存在。"

        op, tp = self.players[operator_id], self.players[target_id]
        if op.guild_id is None or tp.guild_id is None or op.guild_id != tp.guild_id:
            return "双方不在同一帮派。"

        guild = self.guilds[op.guild_id]
        if not self._is_manager(guild, operator_id):
            return "权限不足，需管理层。"
        if target_id == guild.leader_id:
            return "不能踢出帮主。"

        guild.member_ids.discard(target_id)
        guild.deputy_ids.discard(target_id)
        guild.elder_ids.discard(target_id)

        tp.guild_id = None
        tp.guild_role = None
        tp.guild_cooldown_until = self.get_current_day() + self.LEAVE_CD_DAYS
        return f"已踢出成员，目标退帮冷却至第 {tp.guild_cooldown_until} 天。"

    def leave_guild(self, player_id: int) -> str:
        if player_id not in self.players:
            return "玩家不存在。"
        p = self.players[player_id]
        if p.guild_id is None:
            return "你不在帮派中。"

        gid = p.guild_id
        guild = self.guilds.get(gid)
        if not guild:
            p.guild_id = None
            p.guild_role = None
            return "帮派数据异常，已重置你的帮派状态。"

        if player_id == guild.leader_id:
            return "帮主不能直接退帮，请先解散或转让帮主（本白盒未实现转让）。"

        guild.member_ids.discard(player_id)
        guild.deputy_ids.discard(player_id)
        guild.elder_ids.discard(player_id)

        p.guild_id = None
        p.guild_role = None
        p.guild_cooldown_until = self.get_current_day() + self.LEAVE_CD_DAYS
        return f"退帮成功，冷却至第 {p.guild_cooldown_until} 天。"

    def disband_guild(self, leader_id: int) -> str:
        if leader_id not in self.players:
            return "玩家不存在。"
        p = self.players[leader_id]
        if p.guild_id is None:
            return "你不在帮派中。"

        gid = p.guild_id
        guild = self.guilds.get(gid)
        if not guild:
            return "帮派不存在。"
        if guild.leader_id != leader_id:
            return "只有帮主可解散帮派。"

        for mid in list(guild.member_ids):
            mp = self.players[mid]
            mp.guild_id = None
            mp.guild_role = None
            mp.guild_cooldown_until = self.get_current_day() + self.LEAVE_CD_DAYS

        self.guilds.pop(gid, None)
        return f"帮派 {gid} 已解散，全员进入退帮冷却。"

    def assign_role(self, leader_id: int, target_id: int, role: str) -> str:
        """角色分配：仅帮主可设副帮主/长老/帮众。"""
        valid = {"deputy", "elder", "member"}
        if role not in valid:
            return "无效角色。可选：deputy/elder/member"

        if leader_id not in self.players or target_id not in self.players:
            return "玩家不存在。"
        lp, tp = self.players[leader_id], self.players[target_id]
        if lp.guild_id is None or lp.guild_id != tp.guild_id:
            return "双方不在同一帮派。"

        guild = self.guilds[lp.guild_id]
        if guild.leader_id != leader_id:
            return "只有帮主可分配职务。"
        if target_id == leader_id:
            return "帮主角色固定。"

        guild.deputy_ids.discard(target_id)
        guild.elder_ids.discard(target_id)
        if role == "deputy":
            guild.deputy_ids.add(target_id)
        elif role == "elder":
            guild.elder_ids.add(target_id)

        tp.guild_role = role
        return f"成员 {target_id} 职务已设置为 {role}。"

    def list_guild(self, guild_id: int) -> List[str]:
        if guild_id not in self.guilds:
            return ["帮派不存在。"]
        g = self.guilds[guild_id]
        out = [
            f"GID={g.guild_id} 名称={g.name} 活跃度={g.activity}",
            f"公告：{g.notice}",
            f"帮主：{g.leader_id}",
            f"副帮主：{sorted(g.deputy_ids)}",
            f"长老：{sorted(g.elder_ids)}",
            f"成员总数：{len(g.member_ids)}"
        ]
        return out


# =========================
# 8) 总控系统（主交互）
# =========================
class SocialSystem:
    def __init__(self):
        self.players: Dict[int, Player] = {}
        self.current_day = 1

        self.friend_system = FriendSystem(self.players)
        self.mentor_system = MentorshipSystem(self.players, self.get_current_day)
        self.brotherhood_system = BrotherhoodSystem(self.players, self.get_current_day)
        self.romance_system = RomanceSystem(self.players, self.get_current_day)
        self.guild_system = GuildSystem(self.players, self.get_current_day)

    def get_current_day(self) -> int:
        return self.current_day

    def advance_day(self, days: int) -> str:
        if days <= 0:
            return "推进天数必须 > 0。"
        self.current_day += days
        msgs = self.mentor_system.auto_cleanup_inactive()
        return f"时间已推进到第 {self.current_day} 天。\n" + "\n".join(msgs)

    def create_player(self, player_id: int, nickname: str, level: int) -> str:
        if player_id in self.players:
            return "玩家ID已存在。"
        if level < 1:
            return "等级不能小于 1。"
        self.players[player_id] = Player(
            player_id=player_id,
            nickname=nickname,
            level=level,
            online=True,
            last_online_day=self.current_day
        )
        return f"玩家创建成功：ID={player_id}, 昵称={nickname}, 等级={level}"

    def set_online(self, player_id: int, online: bool) -> str:
        if player_id not in self.players:
            return "玩家不存在。"
        p = self.players[player_id]
        p.online = online
        if online:
            p.last_online_day = self.current_day
        return f"玩家 {player_id} 状态已设置为 {'在线' if online else '离线'}。"

    def set_level(self, player_id: int, new_level: int) -> str:
        if player_id not in self.players:
            return "玩家不存在。"
        if new_level < 1:
            return "等级不能小于1。"
        p = self.players[player_id]
        old = p.level
        p.level = new_level
        msgs = [f"玩家 {player_id} 等级：{old} -> {new_level}"]

        # 升到60触发自动毕业
        if old < 60 <= new_level:
            msgs.extend(self.mentor_system.auto_graduate_if_needed(player_id))
        return "\n".join(msgs)

    def list_players(self) -> List[str]:
        out = []
        for pid in sorted(self.players):
            p = self.players[pid]
            out.append(
                f"ID={pid} 昵称={p.nickname} 等级={p.level} 状态={'在线' if p.online else '离线'} "
                f"好友={len(p.friend_groups.get('默认分组', set()))} "
                f"师父数={len(p.master_ids)} 徒弟数={len(p.apprentice_ids)} "
                f"结义={p.jieyi_group_id} 侠侣={p.lover_id} 帮派={p.guild_id}/{p.guild_role} 金币={p.coins}"
            )
        return out if out else ["暂无玩家。"]

    def print_menu(self):
        print("\n==== 武侠MMO社交系统白盒（主菜单）====")
        print(f"当前系统日：第 {self.current_day} 天")
        print("1. 玩家管理")
        print("2. 基础好友系统")
        print("3. 师徒系统")
        print("4. 结义金兰系统")
        print("5. 侠侣结缘系统")
        print("6. 帮派帮会系统")
        print("7. 推进系统时间")
        print("0. 退出")

    # ---------- 玩家管理 ----------
    def menu_player(self):
        while True:
            print("\n--- 玩家管理 ---")
            print("1. 创建玩家")
            print("2. 查看玩家列表")
            print("3. 设置在线/离线")
            print("4. 设置玩家等级")
            print("0. 返回")
            c = input("请选择：").strip()

            if c == "1":
                pid = read_int("输入玩家ID：")
                name = input("输入昵称：").strip()
                lv = read_int("输入等级：")
                print(self.create_player(pid, name, lv))
            elif c == "2":
                for line in self.list_players():
                    print(line)
            elif c == "3":
                pid = read_int("输入玩家ID：")
                val = input("在线? (y/n)：").strip().lower() == "y"
                print(self.set_online(pid, val))
            elif c == "4":
                pid = read_int("输入玩家ID：")
                lv = read_int("输入新等级：")
                print(self.set_level(pid, lv))
            elif c == "0":
                return
            else:
                print("无效选项。")

    # ---------- 好友 ----------
    def menu_friend(self):
        while True:
            print("\n--- 基础好友系统 ---")
            print("1. 发起好友申请")
            print("2. 处理好友申请（同意/拒绝）")
            print("3. 增加亲密度（组队/私聊/任务）")
            print("4. 查看好友列表")
            print("5. 删除好友")
            print("6. 预留拉黑接口说明")
            print("0. 返回")
            c = input("请选择：").strip()

            if c == "1":
                a = read_int("申请方ID：")
                b = read_int("被申请方ID：")
                print(self.friend_system.send_request(a, b))
            elif c == "2":
                target = read_int("处理方ID（收到申请的人）：")
                req = read_int("申请方ID：")
                accept = input("同意? (y/n)：").strip().lower() == "y"
                print(self.friend_system.respond_request(target, req, accept))
            elif c == "3":
                a = read_int("玩家A ID：")
                b = read_int("玩家B ID：")
                print("行为选项：1组队(+20) 2私聊(+8) 3一起任务(+25)")
                ac = input("选择：").strip()
                if ac == "1":
                    print(self.friend_system.increase_intimacy(a, b, 20, "组队"))
                elif ac == "2":
                    print(self.friend_system.increase_intimacy(a, b, 8, "私聊"))
                elif ac == "3":
                    print(self.friend_system.increase_intimacy(a, b, 25, "一起任务"))
                else:
                    print("无效选项。")
            elif c == "4":
                pid = read_int("玩家ID：")
                for line in self.friend_system.view_friend_list(pid):
                    print(line)
            elif c == "5":
                a = read_int("玩家A ID：")
                b = read_int("玩家B ID：")
                print(self.friend_system.remove_friend(a, b))
            elif c == "6":
                pid = read_int("玩家ID：")
                tid = read_int("目标ID：")
                print(self.friend_system.reserve_block_interface(pid, tid))
            elif c == "0":
                return
            else:
                print("无效选项。")

    # ---------- 师徒 ----------
    def menu_mentor(self):
        while True:
            print("\n--- 师徒系统 ---")
            print("1. 建立师徒关系")
            print("2. 完成每日师徒任务（需组队）")
            print("3. 完成周常师徒任务（需组队）")
            print("4. 手动解除师徒关系")
            print("5. 查看师徒关系")
            print("6. 查看玩家良师信息")
            print("0. 返回")
            c = input("请选择：").strip()

            if c == "1":
                m = read_int("师父ID：")
                a = read_int("徒弟ID：")
                print(self.mentor_system.bind(m, a))
            elif c == "2":
                m = read_int("师父ID：")
                a = read_int("徒弟ID：")
                teamed = input("是否组队? (y/n)：").strip().lower() == "y"
                print(self.mentor_system.complete_daily_task(m, a, teamed))
            elif c == "3":
                m = read_int("师父ID：")
                a = read_int("徒弟ID：")
                teamed = input("是否组队? (y/n)：").strip().lower() == "y"
                print(self.mentor_system.complete_weekly_task(m, a, teamed))
            elif c == "4":
                m = read_int("师父ID：")
                a = read_int("徒弟ID：")
                print(self.mentor_system.dissolve(m, a, "手动解除"))
            elif c == "5":
                for line in self.mentor_system.list_relations():
                    print(line)
            elif c == "6":
                pid = read_int("玩家ID：")
                if pid not in self.players:
                    print("玩家不存在。")
                else:
                    p = self.players[pid]
                    rank_name = MentorshipSystem.RANKS[p.mentor_rank - 1]
                    print(f"良师值={p.mentor_value}，良师等级={rank_name}({p.mentor_rank}/5)")
            elif c == "0":
                return
            else:
                print("无效选项。")

    # ---------- 结义 ----------
    def menu_jieyi(self):
        while True:
            print("\n--- 结义金兰系统 ---")
            print("1. 发起结义（2~5人）")
            print("2. 退出结义")
            print("3. 解散结义")
            print("4. 查看结义列表")
            print("0. 返回")
            c = input("请选择：").strip()

            if c == "1":
                raw = input("输入成员ID，逗号分隔（示例: 1,2,3）：").strip()
                ids = [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
                if not ids:
                    print("成员输入无效。")
                    continue

                # 结义流程模拟：全员同意
                all_ok = True
                for pid in ids:
                    ok = input(f"玩家 {pid} 是否同意结义? (y/n)：").strip().lower() == "y"
                    if not ok:
                        all_ok = False
                        break
                if not all_ok:
                    print("结义流程终止：存在成员未同意。")
                    continue

                name = input("输入结义名号：").strip() or "江湖金兰"
                titles = {}
                for pid in ids:
                    t = input(f"输入玩家 {pid} 结义称号：").strip() or "金兰侠士"
                    titles[pid] = t
                print(self.brotherhood_system.create_group(ids, name, titles))
            elif c == "2":
                pid = read_int("玩家ID：")
                print(self.brotherhood_system.leave_group(pid))
            elif c == "3":
                pid = read_int("操作者ID（任一成员）：")
                confirm = input("确认全员解散? (y/n)：").strip().lower() == "y"
                if not confirm:
                    print("已取消。")
                else:
                    print(self.brotherhood_system.disband_group(pid))
            elif c == "4":
                for line in self.brotherhood_system.list_groups():
                    print(line)
            elif c == "0":
                return
            else:
                print("无效选项。")

    # ---------- 侠侣 ----------
    def menu_romance(self):
        while True:
            print("\n--- 侠侣结缘系统 ---")
            print("1. 提升双方亲密度（组队/私聊/互赠礼物）")
            print("2. 发起结缘")
            print("3. 解除结缘（协议/单方）")
            print("4. 查看亲密阶段")
            print("0. 返回")
            c = input("请选择：").strip()

            if c == "1":
                a = read_int("玩家A ID：")
                b = read_int("玩家B ID：")
                print("1组队 2私聊 3互赠礼物")
                ac = input("选择：").strip()
                mapping = {"1": "组队", "2": "私聊", "3": "互赠礼物"}
                if ac not in mapping:
                    print("无效选项。")
                    continue
                print(self.romance_system.add_intimacy_action(a, b, mapping[ac]))
            elif c == "2":
                a = read_int("玩家A ID：")
                b = read_int("玩家B ID：")
                ok = input("双方是否都同意结缘? (y/n)：").strip().lower() == "y"
                if not ok:
                    print("结缘失败：未达成双方同意。")
                else:
                    print(self.romance_system.bind(a, b))
            elif c == "3":
                a = read_int("玩家A ID：")
                b = read_int("玩家B ID：")
                print("1协议解除 2单方解除")
                mode = input("选择：").strip()
                if mode == "1":
                    print(self.romance_system.dissolve(a, b, "协议"))
                elif mode == "2":
                    print(self.romance_system.dissolve(a, b, "单方"))
                else:
                    print("无效选项。")
            elif c == "4":
                a = read_int("玩家A ID：")
                b = read_int("玩家B ID：")
                stage = self.romance_system.get_intimacy_stage(a, b)
                intimacy = self.players.get(a).friend_intimacy.get(b, 0) if a in self.players else 0
                print(f"亲密度={intimacy}，阶段={stage}")
            elif c == "0":
                return
            else:
                print("无效选项。")

    # ---------- 帮派 ----------
    def menu_guild(self):
        while True:
            print("\n--- 帮派帮会系统 ---")
            print("1. 创建帮派")
            print("2. 申请入帮")
            print("3. 审批入帮申请")
            print("4. 查看帮派信息")
            print("5. 编辑帮派公告")
            print("6. 完成帮派日常任务")
            print("7. 职务分配（帮主）")
            print("8. 踢出成员")
            print("9. 主动退帮")
            print("10. 解散帮派（帮主）")
            print("0. 返回")
            c = input("请选择：").strip()

            if c == "1":
                pid = read_int("创建者ID：")
                name = input("帮派名称：").strip() or "无名帮"
                print(self.guild_system.create_guild(pid, name))
            elif c == "2":
                pid = read_int("申请者ID：")
                gid = read_int("目标帮派ID：")
                print(self.guild_system.apply_join(pid, gid))
            elif c == "3":
                admin = read_int("审批者ID：")
                gid = read_int("帮派ID：")
                target = read_int("申请玩家ID：")
                acc = input("同意? (y/n)：").strip().lower() == "y"
                print(self.guild_system.review_application(admin, gid, target, acc))
            elif c == "4":
                gid = read_int("帮派ID：")
                for line in self.guild_system.list_guild(gid):
                    print(line)
            elif c == "5":
                op = read_int("操作者ID：")
                gid = read_int("帮派ID：")
                notice = input("新公告：").strip()
                print(self.guild_system.edit_notice(op, gid, notice))
            elif c == "6":
                pid = read_int("玩家ID：")
                print(self.guild_system.complete_daily_task(pid))
            elif c == "7":
                leader = read_int("帮主ID：")
                target = read_int("目标成员ID：")
                role = input("目标角色(deputy/elder/member)：").strip()
                print(self.guild_system.assign_role(leader, target, role))
            elif c == "8":
                op = read_int("操作者ID：")
                target = read_int("目标成员ID：")
                print(self.guild_system.kick_member(op, target))
            elif c == "9":
                pid = read_int("玩家ID：")
                print(self.guild_system.leave_guild(pid))
            elif c == "10":
                leader = read_int("帮主ID：")
                confirm = input("确认解散? (y/n)：").strip().lower() == "y"
                if not confirm:
                    print("已取消。")
                else:
                    print(self.guild_system.disband_guild(leader))
            elif c == "0":
                return
            else:
                print("无效选项。")

    # ---------- 主循环 ----------
    def run(self):
        while True:
            self.print_menu()
            c = input("请选择：").strip()
            if c == "1":
                self.menu_player()
            elif c == "2":
                self.menu_friend()
            elif c == "3":
                self.menu_mentor()
            elif c == "4":
                self.menu_jieyi()
            elif c == "5":
                self.menu_romance()
            elif c == "6":
                self.menu_guild()
            elif c == "7":
                days = read_int("推进天数：")
                print(self.advance_day(days))
            elif c == "0":
                print("系统已退出。")
                break
            else:
                print("无效选项。")


# =========================
# 9) 工具函数 + main入口
# =========================
def read_int(prompt: str) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            return int(raw)
        except ValueError:
            print("请输入有效整数。")


def main():
    system = SocialSystem()
    print("欢迎进入：武侠MMO社交系统白盒（命令行版）")
    print("建议演示顺序：创建玩家 -> 好友 -> 师徒/结义/结缘 -> 帮派")
    system.run()


if __name__ == "__main__":
    main()