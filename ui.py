"""
命令行交互 UI
"""
import os
import sys
import time
from typing import List, Optional, Any


class GameUI:
    """命令行 UI 交互"""

    def __init__(self, reveal_log: bool = True):
        self.reveal_log = reveal_log

    def clear_screen(self):
        os.system("clear" if os.name != "nt" else "cls")

    def show_info(self, msg: str):
        print(msg)

    def wait_to_continue(self, prompt: str = "按回车继续..."):
        input(prompt)

    def private_input(self, player: Any, prompt: str) -> str:
        self.clear_screen()
        print(f"[仅 {player.name} 查看]")
        return input(prompt)

    def select_player(self, game_engine: Any, player: Any, prompt: str, exclude: Optional[List[int]] = None) -> Optional[int]:
        exclude = exclude or []
        candidates = [p for p in game_engine.players if p.id != player.id and p.id not in exclude]
        if not candidates:
            print("没有可选玩家")
            return None
        while True:
            self.clear_screen()
            print(f"[仅 {player.name} 查看]")
            print(prompt)
            for p in candidates:
                print(f"{p.id}. {p.name}")
            sel = input("输入编号 (或回车取消): ")
            if sel.strip() == "":
                return None
            try:
                v = int(sel)
                if any(p.id == v for p in candidates):
                    return v - 1  # 返回索引
            except ValueError:
                pass

    def discussion_timer(self, seconds: int):
        self.clear_screen()
        print("进入讨论阶段。按回车可跳过计时。")
        start = time.time()
        while True:
            remaining = seconds - int(time.time() - start)
            if remaining <= 0:
                print("讨论时间结束。")
                break
            print(f"剩余: {remaining} 秒 ", end="\r")
            if self._stdin_ready():
                _ = sys.stdin.readline()
                print("\n已跳过计时。")
                break
            time.sleep(0.2)

    def _stdin_ready(self) -> bool:
        try:
            import select
            return select.select([sys.stdin], [], [], 0)[0] != []
        except Exception:
            return False

    def collect_votes(self, game_engine: Any):
        print("进入投票阶段（热座保密，逐人投票）")
        for player in game_engine.players:
            self.clear_screen()
            print(f"[仅 {player.name} 投票]")
            while True:
                for p in game_engine.players:
                    print(f"{p.id}. {p.name}")
                sel = input("选择你要投票的人（不能投自己）：")
                try:
                    v = int(sel)
                    if v == player.id:
                        print("不能投自己。重选。")
                        continue
                    if 1 <= v <= len(game_engine.players):
                        player.vote(v)
                        break
                except ValueError:
                    pass
            print("投票已记录。")
            self.wait_to_continue()


