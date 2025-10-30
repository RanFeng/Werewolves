"""
LangChain 1.0 工具封装

本模块将游戏引擎的若干“对外能力”封装为可被大模型（Agent）直接调用的 Tool。

使用方式（示例）：
1) 在创建好 `GameEngine` 实例后，调用 `set_engine(engine)` 注入引擎。
2) 将下列工具注册到你的 Agent/Toolkit 中（均为同步函数工具）。

工具列表：
- view_initial_role_tool: 查看自己的初始角色
- get_history_speeches_tool: 获取全局历史发言
- speak_tool: 发言
- vote_tool: 投票
- night_action_tool: 夜晚操作（无UI、结构化参数）

注：
- 为便于 LangChain 处理，这些工具的返回值尽量为字符串（必要时返回 JSON 字符串）。
  如需结构化处理，可在上层再做 JSON 解析。
"""

from typing import Optional, List, Dict, Any
import json
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from game_engine import GameEngine


_ENGINE: Optional[GameEngine] = None


def set_engine(engine: GameEngine) -> None:
    """
    注入当前对局的 `GameEngine` 实例。

    必须在使用任何工具前调用一次。
    """
    global _ENGINE
    _ENGINE = engine


class ViewInitialRoleInput(BaseModel):
    """查看自己初始角色的入参"""
    player_id: int = Field(..., description="玩家ID（1-6）")


@tool("view_initial_role", args_schema=ViewInitialRoleInput)
def view_initial_role_tool(player_id: int) -> str:
    """
    查看并返回“自己”的初始身份。

    使用场景：
    - 玩家需要确认自己开局时分到的身份牌。

    参数：
    - player_id: 玩家ID（1-6）。

    返回：
    - 角色名字符串，如“狼人/预言家/强盗/……”；若失败返回“未知/错误信息”。
    """

    try:
        return _ENGINE.view_initial_role(player_id)
    except Exception as exc:
        return f"查看失败: {exc}"


@tool("get_history_speeches")
def get_history_speeches_tool() -> str:
    """
    获取全局的历史发言列表（只读）。

    返回：
    - JSON 字符串数组，每项包含：
      {"idx": 发言序号, "player_id": 玩家ID, "name": 玩家名, "content": 发言内容}
    """

    try:
        speeches = _ENGINE.get_speeches()
        return json.dumps(speeches, ensure_ascii=False)
    except Exception as exc:
        return f"获取失败: {exc}"


class SpeakInput(BaseModel):
    """发言的入参"""
    player_id: int = Field(..., description="玩家ID（1-6）")
    content: str = Field(..., description="发言内容，建议简明扼要")


@tool("speak", args_schema=SpeakInput)
def speak_tool(player_id: int, content: str) -> str:
    """
    以指定玩家身份记录一条发言。

    参数：
    - player_id: 玩家ID（1-6）
    - content: 发言内容

    返回：
    - 成功/失败的提示字符串。
    """

    try:
        _ENGINE.player_speak(player_id, content)
        return "发言已记录"
    except Exception as exc:
        return f"发言失败: {exc}"


class VoteInput(BaseModel):
    """投票的入参"""
    voter_id: int = Field(..., description="投票人ID（1-6）")
    target_id: int = Field(..., description="被投票的玩家ID（1-6）")


@tool("vote", args_schema=VoteInput)
def vote_tool(voter_id: int, target_id: int) -> str:
    """
    记录一张投票（投票阶段使用）。

    规则：
    - 不能投自己。
    - 必须是合法玩家ID。

    返回：
    - "OK" 表示投票成功；否则返回失败原因。
    """

    try:
        ok = _ENGINE.cast_vote(voter_id, target_id)
        return "OK" if ok else "投票无效"
    except Exception as exc:
        return f"投票失败: {exc}"


class NightActionInput(BaseModel):
    """
    夜晚操作的入参（无UI、结构化）。

    说明：参数随玩家当下的“当前角色”而异。请按下列约定提供：
    - 狼人（独狼可选）：{"view_center_index": 0|1|2|3}
    - 爪牙：{}
    - 预言家：
        选其一：{"inspect_player_id": int} 或 {"inspect_centers": [i,j]}（i/j∈{1,2,3}）
    - 强盗：{"swap_with_player_id": int} 或 {"swap": false}
    - 捣蛋鬼：{"swap_player_id_1": int, "swap_player_id_2": int}
    - 酒鬼：{"center_index": 1|2|3}
    - 失眠者：{}
    """
    player_id: int = Field(..., description="玩家ID（1-6）")
    params: Dict[str, Any] = Field(default_factory=dict, description="角色所需的结构化参数")


@tool("night_action", args_schema=NightActionInput)
def night_action_tool(player_id: int, params: Dict[str, Any]) -> str:
    """
    执行一名玩家的夜晚行动（非交互、可编程输入）。

    注意：会直接修改游戏状态（例如交换身份）。

    返回：
    - JSON 字符串，形如 {"log": 日志, "updated_roles": 可选的角色更新映射}
    """

    try:
        result = _ENGINE.perform_night_action(player_id, params)
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return f"执行失败: {exc}"


# =========================
# 分角色的夜晚操作工具
# =========================

class WerewolfInput(BaseModel):
    """
    狼人（Werewolf）的夜晚操作入参。

    使用说明（严格遵循游戏规则）：
    - 若场上“只有一名狼人”（独狼），你可以选择查看中央区的 1 张牌；
      使用 `view_center_index` 指定：
        - 0 表示不查看；
        - 1 / 2 / 3 表示查看中央第 1 / 2 / 3 张。
    - 若场上有 2 名（或更多改版里）狼人，则你不会查看中央牌，而是“看到你的狼人同伴是谁”。

    返回副作用：不会改变任何身份，仅产生日志信息。
    """
    player_id: int = Field(..., description="玩家ID（1-6）")
    view_center_index: int = Field(0, description="0/1/2/3；0 表示不查看")


@tool("night_werewolf", args_schema=WerewolfInput)
def night_werewolf_tool(player_id: int, view_center_index: int = 0) -> str:
    """
    狼人（Werewolf）夜晚行动。

    逻辑摘要：
    - 独狼可选择查看中央 1 张牌；
    - 否则看到同伴名单；
    - 不会修改任何玩家/中央的身份。

    典型调用：
    - {"player_id": 1, "view_center_index": 2}
    - {"player_id": 4}  # 不查看中央
    """

    try:
        result = _ENGINE.perform_night_action(player_id, {"view_center_index": view_center_index})
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return f"执行失败: {exc}"


class MinionInput(BaseModel):
    """
    爪牙（Minion）的夜晚操作入参。

    说明：
    - 爪牙在夜晚会“看到狼人是谁”；若场上没有狼人，则记录“无狼且你若任意一人出局即可单独胜利”的信息。
    - 无需额外参数。
    - 不会修改任何身份。
    """
    player_id: int = Field(..., description="玩家ID（1-6）")


@tool("night_minion", args_schema=MinionInput)
def night_minion_tool(player_id: int) -> str:
    """
    爪牙（Minion）夜晚行动：查看场上狼人名单或无狼信息。
    """

    try:
        result = _ENGINE.perform_night_action(player_id, {})
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return f"执行失败: {exc}"


class SeerInspectPlayerInput(BaseModel):
    """
    预言家（Seer）夜晚操作：分支一（查看一名玩家）。

    规则要点：
    - 在“查看玩家”与“查看两张中央”中二选一，此为“查看玩家”分支；
    - 参数 `inspect_player_id` 为被查看的玩家；
    - 仅返回信息，不会更改身份。
    """
    player_id: int = Field(..., description="预言家玩家ID（1-6）")
    inspect_player_id: int = Field(..., description="被查看玩家ID（1-6）")


@tool("night_seer_inspect_player", args_schema=SeerInspectPlayerInput)
def night_seer_inspect_player_tool(player_id: int, inspect_player_id: int) -> str:
    """
    预言家（Seer）：查看一名玩家当前身份并记录日志。

    典型调用：
    - {"player_id": 2, "inspect_player_id": 5}
    """

    try:
        result = _ENGINE.perform_night_action(player_id, {"inspect_player_id": inspect_player_id})
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return f"执行失败: {exc}"


class SeerInspectCentersInput(BaseModel):
    """
    预言家（Seer）夜晚操作：分支二（查看中央两张）。

    规则要点：
    - 必须提供两张不同的中央牌索引 `i` 与 `j`，取值均为 1-3；
    - 返回两张对应中央牌的信息；
    - 不会更改身份与中央牌。
    """
    player_id: int = Field(..., description="预言家玩家ID（1-6）")
    i: int = Field(..., description="第一张中央牌索引（1-3）")
    j: int = Field(..., description="第二张中央牌索引（1-3，且不同于第一张）")


@tool("night_seer_inspect_centers", args_schema=SeerInspectCentersInput)
def night_seer_inspect_centers_tool(player_id: int, i: int, j: int) -> str:
    """
    预言家（Seer）：查看中央两张牌并记录日志。

    典型调用：
    - {"player_id": 2, "i": 1, "j": 3}
    """

    try:
        params = {"inspect_centers": [i, j]}
        result = _ENGINE.perform_night_action(player_id, params)
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return f"执行失败: {exc}"


class RobberSwapInput(BaseModel):
    """
    强盗（Robber）夜晚操作：与一名玩家交换身份。

    规则要点：
    - 必须指定 `swap_with_player_id`；
    - 执行后“强盗玩家与目标玩家的当前身份将互换”，属于“会修改身份的操作”。
    - 返回中附带 `updated_roles`，记录发生变化的玩家ID与其新身份。
    """
    player_id: int = Field(..., description="强盗玩家ID（1-6）")
    swap_with_player_id: int = Field(..., description="要交换的玩家ID（1-6）")


@tool("night_robber_swap", args_schema=RobberSwapInput)
def night_robber_swap_tool(player_id: int, swap_with_player_id: int) -> str:
    """
    强盗（Robber）：与目标玩家交换身份并返回更新日志与变更映射。

    典型调用：
    - {"player_id": 3, "swap_with_player_id": 5}
    """

    try:
        result = _ENGINE.perform_night_action(player_id, {"swap_with_player_id": swap_with_player_id})
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return f"执行失败: {exc}"


class RobberSkipInput(BaseModel):
    """
    强盗（Robber）夜晚操作：选择“不交换”。

    说明：
    - 明确表示本回合放弃交换（有助于 Agent 意图清晰）。
    - 不会修改任何身份。
    """
    player_id: int = Field(..., description="强盗玩家ID（1-6）")


@tool("night_robber_skip", args_schema=RobberSkipInput)
def night_robber_skip_tool(player_id: int) -> str:
    """
    强盗（Robber）：不交换，记录对应日志。
    """

    try:
        result = _ENGINE.perform_night_action(player_id, {"swap": False})
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return f"执行失败: {exc}"


class TroublemakerSwapInput(BaseModel):
    """
    捣蛋鬼（Troublemaker）夜晚操作：交换两名“其他玩家”的身份。

    规则要点：
    - 必须指定两名不同且不为“自己”的玩家ID；
    - 执行后两名目标玩家的身份互换；
    - 属于“会修改身份的操作”，返回包含 `updated_roles` 的变更映射。
    """
    player_id: int = Field(..., description="捣蛋鬼玩家ID（1-6）")
    swap_player_id_1: int = Field(..., description="第一位被交换玩家ID（1-6）")
    swap_player_id_2: int = Field(..., description="第二位被交换玩家ID（1-6，且不同于第一位）")


@tool("night_troublemaker_swap", args_schema=TroublemakerSwapInput)
def night_troublemaker_swap_tool(player_id: int, swap_player_id_1: int, swap_player_id_2: int) -> str:
    """
    捣蛋鬼（Troublemaker）：交换两名其他玩家的身份并返回更新信息。

    典型调用：
    - {"player_id": 4, "swap_player_id_1": 2, "swap_player_id_2": 6}
    """

    try:
        params = {"swap_player_id_1": swap_player_id_1, "swap_player_id_2": swap_player_id_2}
        result = _ENGINE.perform_night_action(player_id, params)
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return f"执行失败: {exc}"


class DrunkSwapInput(BaseModel):
    """
    酒鬼（Drunk）夜晚操作：必须与中央的一张牌交换。

    规则要点：
    - `center_index` 取值为 1/2/3；
    - 执行后酒鬼会与该中央牌交换身份，“且不能查看自己的新身份”；
    - 属于“会修改身份的操作”，返回包含 `updated_roles` 的变更映射。
    """
    player_id: int = Field(..., description="酒鬼玩家ID（1-6）")
    center_index: int = Field(..., description="中央牌索引（1-3）")


@tool("night_drunk_swap", args_schema=DrunkSwapInput)
def night_drunk_swap_tool(player_id: int, center_index: int) -> str:
    """
    酒鬼（Drunk）：与中央指定索引的牌交换身份，记录变更。

    典型调用：
    - {"player_id": 5, "center_index": 3}
    """

    try:
        result = _ENGINE.perform_night_action(player_id, {"center_index": center_index})
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return f"执行失败: {exc}"


class InsomniacInput(BaseModel):
    """
    失眠者（Insomniac）夜晚操作：查看“此刻”的自身身份。

    说明：
    - 失眠者在夜晚的很后阶段查看自己“被其他人可能交换后的最终身份”；
    - 仅返回信息，不会修改身份。
    """
    player_id: int = Field(..., description="失眠者玩家ID（1-6）")


@tool("night_insomniac_check", args_schema=InsomniacInput)
def night_insomniac_check_tool(player_id: int) -> str:
    """
    失眠者（Insomniac）：查看当前的自己身份并记录日志。
    """

    try:
        result = _ENGINE.perform_night_action(player_id, {})
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return f"执行失败: {exc}"


def all_tools():
    """便捷函数：返回本模块导出的全部工具列表。"""
    return [
        view_initial_role_tool,
        get_history_speeches_tool,
        speak_tool,
        vote_tool,
        # 汇总夜晚操作（通用 + 细分）
        night_action_tool,
        night_werewolf_tool,
        night_minion_tool,
        night_seer_inspect_player_tool,
        night_seer_inspect_centers_tool,
        night_robber_swap_tool,
        night_robber_skip_tool,
        night_troublemaker_swap_tool,
        night_drunk_swap_tool,
        night_insomniac_check_tool,
    ]


