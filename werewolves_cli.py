"""
一夜狼人杀（CLI 热座版）入口
"""
import argparse
from typing import List
from game_engine import GameEngine
from ui import GameUI
from resolver import VoteResolver


def parse_args():
    parser = argparse.ArgumentParser(description="一夜狼人杀（CLI 热座版）")
    parser.add_argument("--names", type=str, default="P1,P2,P3,P4,P5,P6", help="6名玩家名，逗号分隔")
    parser.add_argument("--seed", type=int, default=None, help="随机种子")
    parser.add_argument("--timer", type=int, default=180, help="讨论时长（秒）")
    parser.add_argument("--reveal-log", action="store_true", help="结算后展示夜间日志")
    return parser.parse_args()


def main():
    args = parse_args()
    names: List[str] = [n.strip() for n in args.names.split(",") if n.strip()]
    if len(names) != 6:
        raise SystemExit("当前版本要求恰好6名玩家")

    engine = GameEngine(player_names=names, seed=args.seed)
    ui = GameUI(reveal_log=args.reveal_log)
    engine.ui = ui

    # 流程
    ui.clear_screen()
    ui.show_info("欢迎来到一夜狼人杀！")
    ui.wait_to_continue()

    engine.setup()
    engine.night_phase()
    engine.discussion_phase(duration=args.timer)
    engine.voting_phase()

    # 结算
    resolver = VoteResolver()
    death_ids = resolver.determine_deaths(engine.players)
    win, detail = resolver.check_win_condition(engine.players, engine.center_cards, death_ids)

    ui.clear_screen()
    ui.show_info("=== 结算结果 ===")
    ui.show_info(f"胜负：{win}")
    if detail.get("deaths"):
        ui.show_info("出局玩家：" + ", ".join(f"{p.id}.{p.name}({p.current_role.value})" for p in engine.players if p.id in detail["deaths"]))
    else:
        ui.show_info("无人出局")

    ui.show_info("\n最终身份：")
    for p in engine.players:
        ui.show_info(f"{p.id}.{p.name}: {p.current_role.value}")

    if ui.reveal_log:
        ui.show_info("\n夜晚行动日志：")
        for line in engine.night_log:
            ui.show_info("- " + line)


if __name__ == "__main__":
    main()


