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
        self.initial_role: Optional[Role] = None
        self.current_role: Optional[Role] = None
        self.vote_target: Optional[int] = None  # 投票目标的player_id
        self.is_alive = True
    
    def vote(self, target_id: int):
        """投票"""
        self.vote_target = target_id
    
    def reveal_role(self):
        """亮开身份牌"""
        return self.current_role.value if self.current_role else "未知"
    
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
    
    def get_all_players_by_role(self, role: Role) -> List[Player]:
        """获取所有拥有指定角色的玩家"""
        return [p for p in self.players if p.current_role == role]
    
    def get_player_by_id(self, player_id: int) -> Optional[Player]:
        """根据ID获取玩家"""
        for player in self.players:
            if player.id == player_id:
                return player
        return None

