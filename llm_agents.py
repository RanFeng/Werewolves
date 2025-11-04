"""
LLM Agent 系统：将玩家与 LangChain OpenAI 绑定
"""
from typing import List, Optional, Dict, Any
import json
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage

from game_engine import GameEngine, Player
from roles import Role
from role_prompts import get_role_prompt
from lc_tools import (
    set_engine, all_tools,
    night_werewolf_tool, night_minion_tool,
    night_seer_inspect_player_tool, night_seer_inspect_centers_tool,
    night_robber_swap_tool, night_robber_skip_tool,
    night_troublemaker_swap_tool, night_drunk_swap_tool, night_insomniac_check_tool
)
from dotenv import load_dotenv

load_dotenv()

class AgentPlayer:
    """绑定 Player 与 LLM 的 Agent"""

    def __init__(self, player: Player, llm: ChatOpenAI, engine: GameEngine):
        self.player = player
        self.llm = llm
        self.engine = engine
        self.agent_executor = None

    def get_role_night_tools(self, role: Role) -> List:
        """根据角色获取对应的夜晚工具"""
        tools_map = {
            Role.WEREWOLF: [night_werewolf_tool],
            Role.MINION: [night_minion_tool],
            Role.SEER: [night_seer_inspect_player_tool, night_seer_inspect_centers_tool],
            Role.ROBBER: [night_robber_swap_tool, night_robber_skip_tool],
            Role.TROUBLEMAKER: [night_troublemaker_swap_tool],
            Role.DRUNK: [night_drunk_swap_tool],
            Role.INSOMNIAC: [night_insomniac_check_tool],
        }
        return tools_map.get(role, [])

    def execute_night_action(self, role: Role) -> Dict[str, Any]:
        """
        执行夜晚行动：为 Agent 绑定角色对应的工具，让其自主决策

        Returns:
            {"log": str, "success": bool, "error": Optional[str]}
        """
        tools = self.get_role_night_tools(role)
        if not tools:
            return {
                "log": f"{self.player.name} ({role.value}) 无需夜晚行动",
                "success": True
            }

        from roles import Role

        # 构建系统提示
        werewolves = [p.name for p in self.engine.players if p.current_role == Role.WEREWOLF]
        if len(werewolves) > 1 and self.player.current_role == Role.WEREWOLF:
            companions = [w for w in werewolves if w != self.player.name]
            system_msg = f"""你是 {self.player.name}，当前角色是 {role.value}。

游戏状态：
- 你是狼人，你的同伴是：{', '.join(companions)}
- 你需要使用夜晚技能工具执行行动
"""
        elif role == Role.MINION:
            system_msg = f"""你是 {self.player.name}，当前角色是 {role.value}。

游戏状态：
- 你是爪牙，你可以看到场上所有狼人
- 使用 night_minion 工具查看狼人信息
"""
        elif role == Role.SEER:
            other_players = [f"{p.id}.{p.name}" for p in self.engine.players if p.id != self.player.id]
            system_msg = f"""你是 {self.player.name}，当前角色是 {role.value}。

你可以选择：
1. 使用 night_seer_inspect_player 查看一名玩家（玩家ID：{', '.join(other_players)}）
2. 使用 night_seer_inspect_centers 查看中央两张牌（索引1-3中选择两个不同的数字）

请选择一种方式执行你的技能。
"""
        elif role == Role.ROBBER:
            other_players = [f"{p.id}.{p.name}" for p in self.engine.players if p.id != self.player.id]
            system_msg = f"""你是 {self.player.name}，当前角色是 {role.value}。

你可以选择：
1. 使用 night_robber_swap 与一名玩家交换身份（玩家ID：{', '.join(other_players)}）
2. 使用 night_robber_skip 选择不交换

请做出选择。
"""
        elif role == Role.TROUBLEMAKER:
            other_players = [f"{p.id}.{p.name}" for p in self.engine.players if p.id != self.player.id]
            system_msg = f"""你是 {self.player.name}，当前角色是 {role.value}。

你需要交换两名其他玩家的身份（不能是自己）。
可选玩家ID：{', '.join(other_players)}

使用 night_troublemaker_swap 工具，指定两个不同的玩家ID。
"""
        elif role == Role.DRUNK:
            system_msg = f"""你是 {self.player.name}，当前角色是 {role.value}。

你必须与中央的一张牌交换身份。
使用 night_drunk_swap 工具，指定 center_index（1-3）。
"""
        elif role == Role.INSOMNIAC:
            system_msg = f"""你是 {self.player.name}，当前角色是 {role.value}。

使用 night_insomniac_check 工具查看你的最终身份。
"""
        elif role == Role.WEREWOLF and len([p for p in self.engine.players if p.current_role == Role.WEREWOLF]) == 1:
            system_msg = f"""你是 {self.player.name}，当前角色是 {role.value}。

你是独狼！你可以选择查看中央的一张牌（1-3），或不查看（view_center_index=0）。
使用 night_werewolf 工具执行。
"""
        else:
            system_msg = f"""你是 {self.player.name}，当前角色是 {role.value}。请执行你的夜晚行动。"""

        try:
            # 创建 Agent
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_msg),
                ("human", "请执行你的夜晚行动。"),
            ])
            result = self.llm.bind_tools(tools).invoke(prompt.format())

            tool_call = result.tool_calls[0]
            tool_name = tool_call['name']
            tool_args = tool_call['args']

            # 找到对应的工具并执行
            for tool in tools:
                if tool.name == tool_name:
                    output = tool.invoke(tool_args)
                    output = json.loads(output)
                    return {
                        "log": f"{self.player.name} ({role.value}) 执行夜晚行动 {output["log"]}",
                        "success": True,
                        "output": output["log"]
                    }
            return {
                "log": f"{self.player.name} ({role.value}) 未执行夜晚行动",
                "success": True,
                "output": ""
            }
        except Exception as e:
            return {
                "log": f"{self.player.name} 夜晚行动失败: {str(e)}",
                "success": False,
                "error": str(e)
            }

    def get_system_prompt(self):
        # 构建游戏上下文
        other_players = [
            {"id": p.id, "name": p.name}
            for p in self.engine.players if p.id != self.player.id
        ]

        game_context = {
            "night_log": self.player.night_log,
            "player_name": self.player.name,
            "initial_role": self.player.initial_role if self.player.initial_role else "未知",
            "current_role": self.player.current_role if self.player.current_role else "未知",
            "other_players": other_players,
            "speech_history": self.engine.get_speeches(),
            "center_cards_info": [r.value for r in self.engine.center_cards],
        }

        print("game_context", game_context)

        # 获取角色 Prompt
        system_prompt = get_role_prompt(self.player.current_role, game_context)
        return system_prompt
    
    def generate_speech(self, round_num: int = 1) -> str:
        """
        生成白天发言：根据角色绑定 Prompt，让 LLM 生成发言
        
        Args:
            round_num: 发言轮次
        
        Returns:
            发言内容字符串
        """
        # 获取角色 Prompt
        system_prompt = self.get_system_prompt()
        
        # 构建用户消息
        user_prompt = f"""现在是第 {round_num} 轮发言。

请生成你的发言内容。要求：
1. 50-150字
2. 逻辑清晰
3. 基于你的角色和已知信息
4. 用中文表达
5. 直接输出发言内容，不要包含"发言："等前缀

请开始发言："""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            speech = response.content.strip()
            
            # 清理可能的格式标记
            if speech.startswith("发言："):
                speech = speech[3:].strip()
            if speech.startswith("发言"):
                speech = speech[2:].strip()
            
            return speech
        except Exception as e:
            return f"[发言生成失败: {str(e)}]"
    
    def cast_vote_by_llm(self) -> Optional[int]:
        """
        让 LLM 决定投票目标
        
        Returns:
            目标玩家ID，失败返回None
        """
        other_players = [
            f"{p.id}.{p.name}"
            for p in self.engine.players if p.id != self.player.id
        ]
        system_prompt = self.get_system_prompt()

        user_prompt = f"""可选投票目标：{', '.join(other_players)}，
请根据游戏情况，选择一个玩家ID进行投票。直接输出数字（1-6），不要其他内容。"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            vote_str = response.content.strip()
            vote_id = int(vote_str)
            
            # 验证
            if 1 <= vote_id <= len(self.engine.players) and vote_id != self.player.id:
                return vote_id
            
            return None
        except Exception as e:
            print(f"[{self.player.name} 投票失败: {str(e)}]")
            return None


class LLMAgentManager:
    """管理所有 AI 玩家"""
    
    def __init__(self, engine: GameEngine, api_key: Optional[str] = None, model_name: str = "gpt-4o-mini"):
        self.engine = engine
        set_engine(engine)  # 注入引擎到工具模块
        
        # 创建 LLM 实例
        self.llm = ChatOpenAI(
            model=os.getenv("MODEL"),
            base_url=os.getenv("BASEURL"),
            api_key=os.getenv("APIKEY"),
            temperature=0.7
        )
        
        # 为所有玩家创建 Agent
        self.agents: Dict[int, AgentPlayer] = {}
        for player in engine.players:
            self.agents[player.id] = AgentPlayer(player, self.llm, engine)
    
    def execute_night_phase(self):
        """执行夜晚阶段：按顺序为每个角色执行夜晚行动"""
        night_log = []
        
        for role in self.engine.NIGHT_ORDER:
            players_with_role = [
                p for p in self.engine.players 
                if p.current_role == role
            ]
            
            for player in players_with_role:
                agent = self.agents.get(player.id)
                print(f"\n=== {role.value} 行动：{player.name} ===")
                result = agent.execute_night_action(role)
                if result.get("success"):
                    player.night_log = result.get("log", "")
                    night_log.append(result.get("log", ""))
                    print(f"✓ {player.night_log}")
                else:
                    print(f"✗ {result.get('error', '未知错误')}")
        
        # 更新引擎的夜晚日志
        self.engine.night_log.extend(night_log)
    
    def discussion_phase(self, rounds: int = 2):
        """
        讨论阶段：让所有玩家发言
        
        Args:
            rounds: 发言轮数
        """
        # 随机顺序发言
        import random
        player_order = self.engine.players.copy()
        random.shuffle(player_order)

        for round_num in range(1, rounds + 1):
            print(f"\n=== 第 {round_num} 轮发言 ===\n")

            for player in player_order:
                agent = self.agents.get(player.id)
                print(f"\n[{player.name}]")
                speech = agent.generate_speech(round_num)
                print(speech)
                # 记录发言
                self.engine.player_speak(player.id, speech)
                print()
    
    def voting_phase(self):
        """投票阶段：让所有玩家投票"""
        print("\n=== 投票阶段 ===\n")
        
        for player in self.engine.players:
            agent = self.agents.get(player.id)
            if agent:
                print(f"\n[{player.name} 投票中...]")
                vote_target = agent.cast_vote_by_llm()
                if vote_target:
                    self.engine.cast_vote(player.id, vote_target)
                    target_player = self.engine.get_player_by_id(vote_target)
                    print(f"✓ {player.name} 投票给 {target_player.name if target_player else vote_target}")
                else:
                    print(f"✗ {player.name} 投票失败")

