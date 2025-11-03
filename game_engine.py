"""
游戏引擎和玩家类
"""
import random
from typing import List, Optional, Dict, Any
from roles import Role, Faction


class Player:
    """玩家类"""
    
    def __init__(self, player_id: int, name: str):
        self.id = player_id
        self.name = name
        self.night_log = ""
        self.initial_role: Optional[Role] = None
        self.current_role: Optional[Role] = None
        self.vote_target: Optional[int] = None  # 投票目标的player_id
        self.is_alive = True
        self.engine: Optional["GameEngine"] = None  # 回指引擎，用于对外操作
    
    def vote(self, target_id: int):
        """投票（对外接口）"""
        if self.engine:
            self.engine.cast_vote(self.id, target_id)
        else:
            self.vote_target = target_id
    
    def reveal_role(self):
        """亮开身份牌"""
        return self.current_role.value if self.current_role else "未知"

    def view_initial_role(self) -> str:
        """查看自己的初始角色（对外接口）"""
        return self.initial_role.value if self.initial_role else "未知"

    def speak(self, content: str):
        """发表发言（对外接口）"""
        if self.engine:
            self.engine.player_speak(self.id, content)

    def get_history_speeches(self) -> List[Dict[str, Any]]:
        """获取历史发言（全局）（对外接口）"""
        if self.engine:
            return self.engine.get_speeches()
        return []
    
    def __repr__(self):
        return f"Player({self.id}, {self.name}, {self.current_role.value if self.current_role else 'None'})"


class GameEngine:
    """游戏引擎"""
    
    # 6人入门配置：9张角色牌
    SIX_PLAYER_STARTER_ROLES = [
        Role.WEREWOLF,
        Role.WEREWOLF,
        Role.MINION,
        Role.SEER,
        Role.ROBBER,
        Role.TROUBLEMAKER,
        Role.DRUNK,
        Role.INSOMNIAC,
        Role.HUNTER,
    ]
    
    # 夜晚行动顺序
    NIGHT_ORDER = [
        Role.WEREWOLF,
        Role.MINION,
        Role.SEER,
        Role.ROBBER,
        Role.TROUBLEMAKER,
        Role.DRUNK,
        Role.INSOMNIAC,
    ]
    
    def __init__(self, player_names: List[str], seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        
        self.players: List[Player] = []
        self.center_cards: List[Role] = []
        self.night_log: List[str] = []
        self.phase = "setup"
        self.ui: Any = None  # GameUI 实例，稍后注入
        
        # 创建玩家
        for idx, name in enumerate(player_names, 1):
            self.players.append(Player(idx, name))

        # 发言历史
        self.speech_history: List[Dict[str, Any]] = []  # {idx, player_id, name, content}
    
    def setup(self):
        """游戏准备阶段"""
        self.phase = "setup"
        
        # 从配置中随机选择角色
        roles_pool = self.SIX_PLAYER_STARTER_ROLES.copy()
        random.shuffle(roles_pool)
        
        # 分配给玩家和中央牌
        for i, player in enumerate(self.players):
            player.initial_role = roles_pool[i]
            player.current_role = roles_pool[i]
            player.engine = self
        
        # 剩余3张作为中央牌
        self.center_cards = roles_pool[len(self.players):]
        
        # 显示配置信息
        if self.ui:
            role_names = [r.value for r in roles_pool]
            self.ui.show_info(f"本局使用的角色牌: {', '.join(role_names)}")
            self.ui.show_info(f"中央有3张牌: {', '.join([r.value for r in self.center_cards])}")
            
            # 让每位玩家查看初始身份
            for player in self.players:
                self.ui.private_input(player, f"查看你的初始身份 (按回车继续): ")
                self.ui.show_info(f"你的初始身份是: {player.initial_role.value}")
                self.ui.wait_to_continue()
    
    def night_phase(self):
        """夜晚阶段"""
        self.phase = "night"
        self.night_log.clear()
        
        from roles import get_role_action
        
        # 按夜晚顺序执行行动
        for role_to_activate in self.NIGHT_ORDER:
            # 找到所有拥有这个角色的玩家
            players_with_role = [p for p in self.players if p.current_role == role_to_activate]
            
            for player in players_with_role:
                action = get_role_action(role_to_activate)
                if action:
                    if self.ui:
                        self.ui.show_info(f"\n=== {action.get_role_name()}行动 ===")
                        self.ui.private_input(player, f"{player.name}，你是{role_to_activate.value}，按回车继续: ")
                    
                    result = action.execute(self, player)
                    
                    if result and "log" in result:
                        self.night_log.append(result["log"])
                    
                    if self.ui:
                        self.ui.wait_to_continue()
    
    def discussion_phase(self, duration: int = 180):
        """讨论阶段"""
        self.phase = "discussion"
        if self.ui:
            self.ui.discussion_timer(duration)
    
    def voting_phase(self):
        """投票阶段"""
        self.phase = "voting"
        if self.ui:
            self.ui.collect_votes(self)

    # =========================
    # 对外暴露的玩家操作接口
    # =========================

    def view_initial_role(self, player_id: int) -> str:
        player = self.get_player_by_id(player_id)
        return player.view_initial_role() if player else "未知"

    def get_speeches(self) -> List[Dict[str, Any]]:
        return list(self.speech_history)

    def get_player_speeches(self, player_id: int) -> List[Dict[str, Any]]:
        return [s for s in self.speech_history if s.get("player_id") == player_id]

    def player_speak(self, player_id: int, content: str):
        player = self.get_player_by_id(player_id)
        if not player:
            return
        idx = len(self.speech_history) + 1
        entry = {"idx": idx, "player_id": player.id, "name": player.name, "content": content}
        self.speech_history.append(entry)
        if self.ui:
            self.ui.show_info(f"发言记录[{idx}] {player.name}: {content}")

    def cast_vote(self, voter_id: int, target_id: int) -> bool:
        """带校验的投票接口，供外部或UI调用"""
        voter = self.get_player_by_id(voter_id)
        target = self.get_player_by_id(target_id)
        if not voter or not target:
            return False
        if voter.id == target.id:
            return False
        voter.vote_target = target.id
        return True
    
    def get_all_players_by_role(self, role: Role) -> List[Player]:
        """获取所有拥有指定角色的玩家"""
        return [p for p in self.players if p.current_role == role]
    
    def get_player_by_id(self, player_id: int) -> Optional[Player]:
        """根据ID获取玩家"""
        for player in self.players:
            if player.id == player_id:
                return player
        return None

    def perform_night_action(self, player_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        以“无UI、可编程输入”的方式执行夜晚操作，便于对接工具/Agent。

        说明：本方法是对 `roles.py` 中角色执行逻辑的“无交互版”复刻，
        通过结构化的 `params` 传入必要的选择项，直接更新游戏状态并返回行动日志。

        入参约定（按角色区分）：
        - 狼人 WEREWOLF：
          - 若是“独狼”（场上仅此一名狼人），可查看中央 1-3 中的一张。
          - params: {"view_center_index": 0|1|2|3}，0 表示不查看。
        - 爪牙 MINION：
          - 无需参数，返回看到的狼人信息（若无狼人则记录相应信息）。
        - 预言家 SEER：
          - 二选一：
            1) 查看一名玩家：params: {"inspect_player_id": int}
            2) 查看中央两张：params: {"inspect_centers": [i,j]}，i/j∈{1,2,3} 且不重复
        - 强盗 ROBBER：
          - 与一名玩家交换身份，或不交换。
          - params: {"swap_with_player_id": int} 或 {"swap": false}
        - 捣蛋鬼 TROUBLEMAKER：
          - 交换两名其他玩家的身份。
          - params: {"swap_player_id_1": int, "swap_player_id_2": int}
        - 酒鬼 DRUNK：
          - 必须与中央 1-3 的一张交换。
          - params: {"center_index": 1|2|3}
        - 失眠者 INSOMNIAC：
          - 无参数，仅查看自己的最终身份。

        返回：{"log": str, "updated_roles": Optional[Dict[int, Role]]}
        """
        from roles import Role

        player = self.get_player_by_id(player_id)
        if not player:
            return {"log": "玩家不存在"}

        role = player.current_role
        updated_roles: Dict[int, Role] = {}

        if role == Role.WEREWOLF:
            werewolves = [p for p in self.players if p.current_role == Role.WEREWOLF]
            if len(werewolves) == 1:
                idx = int(params.get("view_center_index", 0))
                if 1 <= idx <= 3:
                    center_role = self.center_cards[idx - 1]
                    return {"log": f"{player.name} 查看了中央第{idx}张牌: {center_role.value}"}
                return {"log": f"{player.name} 选择不查看中央牌"}
            else:
                companions = ", ".join(w.name for w in werewolves if w.id != player.id)
                return {"log": f"{player.name} 看到同伴: {companions}"}

        if role == Role.MINION:
            werewolves = [p.name for p in self.players if p.current_role == Role.WEREWOLF]
            if werewolves:
                return {"log": f"{player.name} 看到狼人是: {', '.join(werewolves)}"}
            return {"log": f"{player.name} 发现场上没有狼人"}

        if role == Role.SEER:
            inspect_player_id = params.get("inspect_player_id")
            inspect_centers = params.get("inspect_centers")
            if inspect_player_id is not None:
                target = self.get_player_by_id(int(inspect_player_id))
                if not target:
                    return {"log": f"{player.name} 试图查看的玩家不存在"}
                return {"log": f"{player.name} 查看了 {target.name} 的身份: {target.current_role.value}"}
            if isinstance(inspect_centers, list) and len(inspect_centers) == 2:
                seen = []
                used: set = set()
                for raw in inspect_centers:
                    try:
                        idx = int(raw)
                    except Exception:
                        continue
                    if idx in {1, 2, 3} and idx not in used:
                        used.add(idx)
                        seen.append(f"中央第{idx}张牌: {self.center_cards[idx - 1].value}")
                if seen:
                    return {"log": " | ".join(seen)}
            return {"log": f"{player.name} 未执行行动"}

        if role == Role.ROBBER:
            if params.get("swap") is False and not params.get("swap_with_player_id"):
                return {"log": f"{player.name} 选择不交换身份"}
            target_id = params.get("swap_with_player_id")
            if target_id is None:
                return {"log": f"{player.name} 选择不交换身份"}
            target = self.get_player_by_id(int(target_id))
            if not target or target.id == player.id:
                return {"log": f"{player.name} 交换目标无效"}
            player.current_role, target.current_role = target.current_role, player.current_role
            updated_roles[player.id] = player.current_role
            updated_roles[target.id] = target.current_role
            return {"log": f"{player.name} 与 {target.name} 交换了身份", "updated_roles": updated_roles}

        if role == Role.TROUBLEMAKER:
            a = params.get("swap_player_id_1")
            b = params.get("swap_player_id_2")
            if a is None or b is None or a == b:
                return {"log": f"{player.name} 未执行行动"}
            p1 = self.get_player_by_id(int(a))
            p2 = self.get_player_by_id(int(b))
            if not p1 or not p2 or p1.id == player.id or p2.id == player.id:
                return {"log": f"{player.name} 未执行行动"}
            p1.current_role, p2.current_role = p2.current_role, p1.current_role
            updated_roles[p1.id] = p1.current_role
            updated_roles[p2.id] = p2.current_role
            return {"log": f"{player.name} 交换了 {p1.name} 和 {p2.name} 的身份", "updated_roles": updated_roles}

        if role == Role.DRUNK:
            idx = int(params.get("center_index", 0))
            if idx in (1, 2, 3):
                i = idx - 1
                player.current_role, self.center_cards[i] = self.center_cards[i], player.current_role
                updated_roles[player.id] = player.current_role
                return {"log": f"{player.name} 与中央第{idx}张牌交换了身份", "updated_roles": updated_roles}
            return {"log": f"{player.name} 交换身份失败"}

        if role == Role.INSOMNIAC:
            return {"log": f"{player.name} 查看了自己的最终身份: {player.current_role.value}"}

        return {"log": f"{player.name} 的角色无需/不支持夜晚行动"}

