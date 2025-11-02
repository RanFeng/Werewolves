"""
一夜狼人杀（LLM 自动版）入口
使用 LangChain OpenAI 让大模型参与游戏
"""
import argparse
import os
from typing import List
from game_engine import GameEngine
from resolver import VoteResolver
from llm_agents import LLMAgentManager


def parse_args():
    parser = argparse.ArgumentParser(description="一夜狼人杀（LLM 自动版）")
    parser.add_argument("--names", type=str, default="P1,P2,P3,P4,P5,P6", help="6名玩家名，逗号分隔")
    parser.add_argument("--seed", type=int, default=None, help="随机种子")
    parser.add_argument("--speech-rounds", type=int, default=2, help="发言轮数（默认：2）")
    parser.add_argument("--reveal-log", action="store_true", help="结算后展示夜间日志")
    return parser.parse_args()


def main():
    args = parse_args()
    names: List[str] = [n.strip() for n in args.names.split(",") if n.strip()]
    if len(names) != 6:
        raise SystemExit("当前版本要求恰好6名玩家")
    
    # 创建游戏引擎
    engine = GameEngine(player_names=names, seed=args.seed)
    
    # 创建 LLM Agent 管理器
    agent_manager = LLMAgentManager(
        engine=engine,
    )
    
    print("=" * 60)
    print("一夜狼人杀（LLM 自动版）")
    print("=" * 60)
    print()
    
    # 准备阶段
    print("=== 准备阶段 ===")
    engine.setup()
    
    # 显示角色分配（仅展示，不显示给AI）
    print("\n角色分配（仅显示，AI不会直接看到）：")
    for player in engine.players:
        print(f"  {player.id}. {player.name}: {player.initial_role.value if player.initial_role else '未知'}")
    print()
    
    # 夜晚阶段
    print("=" * 60)
    print("=== 夜晚阶段 ===")
    print("=" * 60)
    agent_manager.execute_night_phase()
    
    # 显示当前身份（仅展示）
    print("\n当前身份（夜晚行动后，仅显示）：")
    for player in engine.players:
        print(f"  {player.id}. {player.name}: {player.current_role.value if player.current_role else '未知'}")
    print()
    
    # 讨论阶段
    print("=" * 60)
    print("=== 讨论阶段 ===")
    print("=" * 60)
    agent_manager.discussion_phase(rounds=args.speech_rounds)
    
    # 投票阶段
    print("=" * 60)
    print("=== 投票阶段 ===")
    print("=" * 60)
    agent_manager.voting_phase()
    
    # 结算
    print("\n" + "=" * 60)
    print("=== 结算结果 ===")
    print("=" * 60)
    
    resolver = VoteResolver()
    death_ids = resolver.determine_deaths(engine.players)
    win, detail = resolver.check_win_condition(engine.players, engine.center_cards, death_ids)
    
    print(f"\n胜负：{win}")
    print(f"原因：{detail.get('reason', '')}")
    
    if detail.get("deaths"):
        print("\n出局玩家：")
        for death_id in detail["deaths"]:
            player = engine.get_player_by_id(death_id)
            if player:
                print(f"  {player.id}. {player.name} ({player.current_role.value if player.current_role else '未知'})")
    else:
        print("\n无人出局")
    
    print("\n最终身份：")
    for player in engine.players:
        initial = player.initial_role.value if player.initial_role else "未知"
        current = player.current_role.value if player.current_role else "未知"
        vote_target = ""
        if player.vote_target:
            target = engine.get_player_by_id(player.vote_target)
            vote_target = f" → 投票给 {target.name if target else player.vote_target}" if target else ""
        print(f"  {player.id}. {player.name}: {initial} → {current}{vote_target}")
    
    if args.reveal_log:
        print("\n夜晚行动日志：")
        for line in engine.night_log:
            print(f"  - {line}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

