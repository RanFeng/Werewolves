"""
角色定义和夜晚行动类
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Any


class Faction(Enum):
    """阵营枚举"""
    WEREWOLF = "狼人阵营"  # 狼人和爪牙
    VILLAGER = "好人阵营"  # 其他所有角色
    THIRD_PARTY = "第三方"  # 皮匠等


class Role(Enum):
    """角色枚举"""
    # 6人入门配置需要的角色
    WEREWOLF = "狼人"
    MINION = "爪牙"
    SEER = "预言家"
    ROBBER = "强盗"
    TROUBLEMAKER = "捣蛋鬼"
    DRUNK = "酒鬼"
    INSOMNIAC = "失眠者"
    HUNTER = "猎人"
    
    def get_faction(self) -> Faction:
        """获取角色所属阵营"""
        if self in [Role.WEREWOLF, Role.MINION]:
            return Faction.WEREWOLF
        return Faction.VILLAGER
    
    def has_night_action(self) -> bool:
        """是否在夜晚有行动"""
        return self not in [Role.HUNTER]


class RoleAction(ABC):
    """角色夜晚行动抽象基类"""
    
    @abstractmethod
    def execute(self, game_engine: Any, player: Any) -> Dict[str, Any]:
        """
        执行夜晚行动
        返回: {"log": str, "updated_roles": dict} 或其他相关信息
        """
        pass
    
    @abstractmethod
    def get_role_name(self) -> str:
        """返回角色名称"""
        pass


class WerewolfAction(RoleAction):
    """狼人行动"""
    
    def get_role_name(self) -> str:
        return "狼人"
    
    def execute(self, game_engine: Any, player: Any) -> Dict[str, Any]:
        from game_engine import GameEngine
        
        log_parts = []
        werewolves = [p for p in game_engine.players if p.current_role == Role.WEREWOLF]
        
        if len(werewolves) == 1:
            # 独狼，可以查看中央一张牌
            log_parts.append(f"{player.name} 是独狼")
            choice = game_engine.ui.private_input(
                player,
                "你是独狼，可以选择查看中央牌中的一张 (1-3)，或不查看 (0): "
            )
            try:
                choice_int = int(choice)
                if 1 <= choice_int <= 3:
                    center_role = game_engine.center_cards[choice_int - 1]
                    log_parts.append(f"{player.name} 查看了中央第{choice_int}张牌: {center_role.value}")
                    game_engine.ui.show_info(f"中央第{choice_int}张牌是: {center_role.value}")
                elif choice_int == 0:
                    log_parts.append(f"{player.name} 选择不查看中央牌")
            except ValueError:
                log_parts.append(f"{player.name} 选择不查看中央牌")
        else:
            # 有同伴
            companions = [w.name for w in werewolves if w != player]
            log_parts.append(f"{player.name} 看到同伴: {', '.join(companions)}")
            game_engine.ui.show_info(f"你的狼人同伴是: {', '.join(companions)}")
        
        return {"log": " | ".join(log_parts)}


class MinionAction(RoleAction):
    """爪牙行动"""
    
    def get_role_name(self) -> str:
        return "爪牙"
    
    def execute(self, game_engine: Any, player: Any) -> Dict[str, Any]:
        from game_engine import GameEngine
        
        werewolves = [p.name for p in game_engine.players if p.current_role == Role.WEREWOLF]
        
        if werewolves:
            log = f"{player.name} 看到狼人是: {', '.join(werewolves)}"
            game_engine.ui.show_info(f"狼人是: {', '.join(werewolves)}")
        else:
            log = f"{player.name} 发现场上没有狼人"
            game_engine.ui.show_info("场上没有狼人！如果任意一人出局，你单独胜利！")
        
        return {"log": log}


class SeerAction(RoleAction):
    """预言家行动"""
    
    def get_role_name(self) -> str:
        return "预言家"
    
    def execute(self, game_engine: Any, player: Any) -> Dict[str, Any]:
        from game_engine import GameEngine
        
        choice = game_engine.ui.private_input(
            player,
            "选择: 1) 查看一位玩家的身份 2) 查看中央2张牌 (输入1或2): "
        )
        
        log_parts = []
        
        if choice == "1":
            # 查看一位玩家
            target_idx = game_engine.ui.select_player(game_engine, player, "选择要查看的玩家")
            if target_idx is not None:
                target = game_engine.players[target_idx]
                log_parts.append(f"{player.name} 查看了 {target.name} 的身份: {target.current_role.value}")
                game_engine.ui.show_info(f"{target.name} 的身份是: {target.current_role.value}")
        elif choice == "2":
            # 查看中央2张牌
            indices = []
            for i in range(2):
                idx = game_engine.ui.private_input(
                    player,
                    f"选择中央第几张牌 (剩余可选: {[j+1 for j in range(3) if j not in indices]}) (1-3): "
                )
                try:
                    idx_int = int(idx) - 1
                    if 0 <= idx_int < 3 and idx_int not in indices:
                        indices.append(idx_int)
                        center_role = game_engine.center_cards[idx_int]
                        log_parts.append(f"中央第{idx_int+1}张牌: {center_role.value}")
                        game_engine.ui.show_info(f"中央第{idx_int+1}张牌是: {center_role.value}")
                except ValueError:
                    pass
        
        return {"log": " | ".join(log_parts) if log_parts else f"{player.name} 未执行行动"}


class RobberAction(RoleAction):
    """强盗行动"""
    
    def get_role_name(self) -> str:
        return "强盗"
    
    def execute(self, game_engine: Any, player: Any) -> Dict[str, Any]:
        from game_engine import GameEngine
        
        choice = game_engine.ui.private_input(
            player,
            "选择: 1) 与一位玩家交换身份 2) 不交换 (输入1或2): "
        )
        
        if choice == "2":
            return {"log": f"{player.name} 选择不交换身份"}
        
        target_idx = game_engine.ui.select_player(game_engine, player, "选择要交换的玩家")
        if target_idx is None:
            return {"log": f"{player.name} 选择不交换身份"}
        
        target = game_engine.players[target_idx]
        
        # 交换身份
        player.current_role, target.current_role = target.current_role, player.current_role
        
        log = f"{player.name} 与 {target.name} 交换了身份"
        game_engine.ui.show_info(f"你现在的身份是: {player.current_role.value}")
        
        return {"log": log, "updated_roles": {player.id: player.current_role, target.id: target.current_role}}


class TroublemakerAction(RoleAction):
    """捣蛋鬼行动"""
    
    def get_role_name(self) -> str:
        return "捣蛋鬼"
    
    def execute(self, game_engine: Any, player: Any) -> Dict[str, Any]:
        from game_engine import GameEngine
        
        # 选择第一位玩家
        target1_idx = game_engine.ui.select_player(game_engine, player, "选择第一位要交换的玩家")
        if target1_idx is None:
            return {"log": f"{player.name} 未执行行动"}
        
        # 选择第二位玩家
        target2_idx = game_engine.ui.select_player(game_engine, player, "选择第二位要交换的玩家", exclude=[target1_idx])
        if target2_idx is None or target2_idx == target1_idx:
            return {"log": f"{player.name} 未执行行动"}
        
        target1 = game_engine.players[target1_idx]
        target2 = game_engine.players[target2_idx]
        
        # 交换身份
        target1.current_role, target2.current_role = target2.current_role, target1.current_role
        
        log = f"{player.name} 交换了 {target1.name} 和 {target2.name} 的身份"
        game_engine.ui.show_info(f"已交换 {target1.name} 和 {target2.name} 的身份")
        
        return {"log": log, "updated_roles": {target1.id: target1.current_role, target2.id: target2.current_role}}


class DrunkAction(RoleAction):
    """酒鬼行动"""
    
    def get_role_name(self) -> str:
        return "酒鬼"
    
    def execute(self, game_engine: Any, player: Any) -> Dict[str, Any]:
        from game_engine import GameEngine
        
        choice = game_engine.ui.private_input(
            player,
            "必须与中央牌交换，选择中央第几张牌 (1-3): "
        )
        
        try:
            choice_int = int(choice)
            if 1 <= choice_int <= 3:
                idx = choice_int - 1
                # 交换身份
                player.current_role, game_engine.center_cards[idx] = game_engine.center_cards[idx], player.current_role
                log = f"{player.name} 与中央第{choice_int}张牌交换了身份"
                game_engine.ui.show_info(f"已交换，你现在不能查看新身份")
                return {"log": log, "updated_roles": {player.id: player.current_role}}
        except ValueError:
            pass
        
        return {"log": f"{player.name} 交换身份失败"}


class InsomniacAction(RoleAction):
    """失眠者行动"""
    
    def get_role_name(self) -> str:
        return "失眠者"
    
    def execute(self, game_engine: Any, player: Any) -> Dict[str, Any]:
        from game_engine import GameEngine
        
        log = f"{player.name} 查看了自己的最终身份: {player.current_role.value}"
        game_engine.ui.show_info(f"你现在的身份是: {player.current_role.value}")
        
        return {"log": log}


# 角色行动映射
ROLE_ACTIONS: Dict[Role, RoleAction] = {
    Role.WEREWOLF: WerewolfAction(),
    Role.MINION: MinionAction(),
    Role.SEER: SeerAction(),
    Role.ROBBER: RobberAction(),
    Role.TROUBLEMAKER: TroublemakerAction(),
    Role.DRUNK: DrunkAction(),
    Role.INSOMNIAC: InsomniacAction(),
}


def get_role_action(role: Role) -> Optional[RoleAction]:
    """获取角色的行动类"""
    return ROLE_ACTIONS.get(role)

