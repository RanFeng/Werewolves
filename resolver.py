"""
投票统计与胜负判定
"""
from typing import Dict, List, Tuple, Set
from collections import defaultdict
from roles import Role, Faction


class VoteResolver:
    """处理票型、死亡与胜负"""

    def count_votes(self, players) -> Dict[int, int]:
        counts: Dict[int, int] = defaultdict(int)
        for p in players:
            if p.vote_target is not None:
                counts[p.vote_target] += 1
        return dict(counts)

    def determine_deaths(self, players) -> List[int]:
        counts = self.count_votes(players)
        if not counts:
            return []
        # 若所有人各得一票，无人死亡
        if len(counts) == len(players) and all(v == 1 for v in counts.values()):
            return []
        max_votes = max(counts.values())
        top = [pid for pid, c in counts.items() if c == max_votes]
        return top

    def apply_hunter_effect(self, players, death_ids: List[int]) -> Set[int]:
        """若猎人死亡，投他票的人也死亡"""
        deaths: Set[int] = set(death_ids)
        id_to_player = {p.id: p for p in players}
        hunter_ids = [pid for pid in deaths if id_to_player.get(pid) and id_to_player[pid].current_role == Role.HUNTER]
        if hunter_ids:
            for hunter_id in hunter_ids:
                for p in players:
                    if p.vote_target == hunter_id:
                        deaths.add(p.id)
        return deaths

    def check_win_condition(self, players, center_cards, death_ids: List[int]) -> Tuple[str, Dict]:
        id_to_player = {p.id: p for p in players}
        deaths_set = set(death_ids)
        deaths_set = self.apply_hunter_effect(players, list(deaths_set))

        # 是否有狼人/爪牙
        alive_roles = [p.current_role for p in players]
        has_werewolf = any(r == Role.WEREWOLF for r in alive_roles)
        has_minion = any(r == Role.MINION for r in alive_roles)

        # 若有狼人
        if has_werewolf:
            # 若死亡列表包含狼人 → 好人胜
            if any(id_to_player[pid].current_role == Role.WEREWOLF for pid in deaths_set if pid in id_to_player):
                return ("好人阵营胜利", {"reason": "狼人被处决", "deaths": sorted(list(deaths_set))})
            # 无人死亡则狼人阵营胜利
            if not deaths_set:
                return ("狼人阵营胜利", {"reason": "无人死亡且场上有狼人", "deaths": []})
            # 有人死但没有狼人死 → 狼人阵营胜利
            return ("狼人阵营胜利", {"reason": "处决的不是狼人", "deaths": sorted(list(deaths_set))})

        # 无狼人
        if not has_werewolf:
            # 若有爪牙
            if has_minion:
                # 爪牙被处决 → 好人胜
                if any(id_to_player[pid].current_role == Role.MINION for pid in deaths_set if pid in id_to_player):
                    return ("好人阵营胜利", {"reason": "无狼人且爪牙被处决", "deaths": sorted(list(deaths_set))})
                # 任意其他人被处决（有人死亡）→ 爪牙胜
                if deaths_set:
                    return ("狼人阵营胜利", {"reason": "无狼人但有人死亡，爪牙胜", "deaths": sorted(list(deaths_set))})
                # 无人死亡 → 好人胜
                return ("好人阵营胜利", {"reason": "无狼人且无人死亡", "deaths": []})
            # 无狼人且无爪牙
            if not deaths_set:
                return ("好人阵营胜利", {"reason": "全为好人且无人死亡", "deaths": []})
            else:
                return ("狼人阵营胜利", {"reason": "全为好人但有人死亡（好人失败）", "deaths": sorted(list(deaths_set))})


